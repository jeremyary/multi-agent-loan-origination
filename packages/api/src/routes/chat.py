# This project was developed with assistance from AI tools.
"""WebSocket chat endpoint for agent conversations.

Protocol:
  Client sends:  {"type": "message", "content": "user text"}
  Server sends:  {"type": "token", "content": "..."} (streamed)
                 {"type": "safety_override", "content": "..."} (output shield replaced response)
                 {"type": "done"} (end of response)
                 {"type": "error", "content": "..."} (on failure)

Audit events are written with the same session_id used for LangFuse traces,
enabling trace-to-audit correlation (S-1-F18-03).
"""

import json
import logging
import uuid

from db import get_db
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from ..agents.registry import get_agent
from ..observability import build_langfuse_config, flush_langfuse
from ..services.audit import write_audit_event

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/chat")
async def chat_websocket(ws: WebSocket):
    """WebSocket endpoint for public assistant chat."""
    await ws.accept()

    try:
        graph = get_agent("public-assistant")
    except Exception:
        logger.exception("Failed to load public-assistant agent")
        await ws.send_json(
            {"type": "error", "content": "Our chat assistant is temporarily unavailable."}
        )
        await ws.close()
        return

    # Conversation history for this WebSocket session
    messages: list = []
    session_id = str(uuid.uuid4())
    langfuse_config = build_langfuse_config(session_id=session_id)
    user_role = "prospect"
    user_id = session_id

    async def _audit(event_type: str, event_data: dict | None = None) -> None:
        """Write an audit event with the shared session_id."""
        try:
            async for db_session in get_db():
                await write_audit_event(
                    db_session,
                    event_type=event_type,
                    session_id=session_id,
                    user_id=user_id,
                    user_role=user_role,
                    event_data=event_data,
                )
                await db_session.commit()
        except Exception:
            logger.debug("Failed to write audit event %s", event_type, exc_info=True)

    try:
        while True:
            raw = await ws.receive_text()
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await ws.send_json({"type": "error", "content": "Invalid JSON"})
                continue

            if data.get("type") != "message" or not data.get("content"):
                await ws.send_json(
                    {"type": "error", "content": "Expected {type: message, content: ...}"}
                )
                continue

            user_text = data["content"]
            messages.append(HumanMessage(content=user_text))

            try:
                full_response = ""
                async for event in graph.astream_events(
                    {
                        "messages": messages,
                        "user_role": user_role,
                        "user_id": user_id,
                    },
                    config=langfuse_config,
                    version="v2",
                ):
                    kind = event.get("event")
                    node = event.get("metadata", {}).get("langgraph_node")

                    if kind == "on_chat_model_stream" and node == "agent":
                        chunk = event.get("data", {}).get("chunk")
                        if isinstance(chunk, AIMessageChunk) and chunk.content:
                            await ws.send_json({"type": "token", "content": chunk.content})
                            full_response += chunk.content

                    elif kind == "on_chain_end" and node == "input_shield":
                        output = event.get("data", {}).get("output")
                        if isinstance(output, dict) and output.get("safety_blocked"):
                            for msg in output.get("messages", []):
                                if hasattr(msg, "content") and msg.content:
                                    await ws.send_json({"type": "token", "content": msg.content})
                                    full_response = msg.content
                            await _audit("safety_block", {"shield": "input", "blocked": True})

                    elif kind == "on_chain_end" and node == "tool_auth":
                        output = event.get("data", {}).get("output")
                        if isinstance(output, dict):
                            auth_msgs = output.get("messages", [])
                            if auth_msgs:
                                logger.info("Tool auth denied for session %s", session_id)
                                await _audit(
                                    "tool_auth_denied",
                                    {
                                        "message": auth_msgs[-1].content
                                        if hasattr(auth_msgs[-1], "content")
                                        else str(auth_msgs[-1]),
                                    },
                                )

                    elif kind == "on_tool_end":
                        tool_output = event.get("data", {}).get("output")
                        tool_name = event.get("name", "unknown")
                        await _audit(
                            "tool_invocation",
                            {
                                "tool_name": tool_name,
                                "result_length": len(str(tool_output)) if tool_output else 0,
                            },
                        )

                    elif kind == "on_chain_end" and node == "output_shield":
                        output = event.get("data", {}).get("output")
                        if isinstance(output, dict):
                            shield_msgs = output.get("messages", [])
                            if shield_msgs:
                                override = shield_msgs[-1].content
                                await ws.send_json({"type": "safety_override", "content": override})
                                full_response = override
                                await _audit(
                                    "safety_block",
                                    {
                                        "shield": "output",
                                        "blocked": True,
                                    },
                                )

                # Add assistant response to history
                if full_response:
                    messages.append(AIMessage(content=full_response))

                await ws.send_json({"type": "done"})

            except Exception:
                logger.exception("Agent invocation failed")
                await ws.send_json(
                    {
                        "type": "error",
                        "content": "Our chat assistant is temporarily unavailable. "
                        "Please try again later.",
                    }
                )

    except WebSocketDisconnect:
        logger.debug("Client disconnected from chat")
    finally:
        flush_langfuse()
