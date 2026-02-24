# This project was developed with assistance from AI tools.
"""WebSocket chat endpoint for agent conversations.

Protocol:
  Client sends:  {"type": "message", "content": "user text"}
  Server sends:  {"type": "token", "content": "..."} (streamed)
                 {"type": "done"} (end of response)
                 {"type": "error", "content": "..."} (on failure)
"""

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from langchain_core.messages import AIMessageChunk, HumanMessage

from ..agents.registry import get_agent

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
                async for event in graph.astream_events({"messages": messages}, version="v2"):
                    kind = event.get("event")
                    if kind == "on_chat_model_stream":
                        # Only stream tokens from the agent node, not the classifier
                        node = event.get("metadata", {}).get("langgraph_node")
                        if node != "agent":
                            continue
                        chunk = event.get("data", {}).get("chunk")
                        if isinstance(chunk, AIMessageChunk) and chunk.content:
                            await ws.send_json({"type": "token", "content": chunk.content})
                            full_response += chunk.content

                # Add assistant response to history
                if full_response:
                    from langchain_core.messages import AIMessage

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
