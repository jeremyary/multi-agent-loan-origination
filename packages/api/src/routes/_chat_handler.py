# This project was developed with assistance from AI tools.
"""Shared WebSocket chat helpers used by public and borrower chat endpoints.

Extracts the streaming loop and WebSocket authentication so both chat.py and
borrower_chat.py share identical event handling + audit writing logic.
"""

import json
import logging

import jwt as pyjwt
from db.enums import UserRole
from fastapi import WebSocket
from langchain_core.messages import AIMessage, AIMessageChunk, HumanMessage

from ..core.auth import build_data_scope
from ..core.config import settings
from ..middleware.auth import _decode_token, _resolve_role
from ..observability import build_langfuse_config, flush_langfuse
from ..schemas.auth import UserContext
from ..services.audit import write_audit_event

logger = logging.getLogger(__name__)


async def authenticate_websocket(
    ws: WebSocket,
    required_role: UserRole | None = None,
) -> UserContext | None:
    """Validate JWT from ``?token=<jwt>`` query param on an already-accepted WebSocket.

    When ``AUTH_DISABLED=true``: returns a dev user whose role matches *required_role*
    (or ADMIN if no role is required).

    Returns ``None`` (and closes the WS) when authentication or authorization fails.
    """
    if settings.AUTH_DISABLED:
        role = required_role or UserRole.ADMIN
        return UserContext(
            user_id="dev-user",
            role=role,
            email="dev@summit-cap.local",
            name="Dev User",
            data_scope=build_data_scope(role, "dev-user"),
        )

    token = ws.query_params.get("token")

    if not token:
        if required_role is not None:
            await ws.close(code=4001, reason="Missing authentication token")
            return None
        # Unauthenticated endpoints (public chat) -- return None to let caller decide
        return None

    try:
        payload = await _decode_token(token)
    except (pyjwt.ExpiredSignatureError, pyjwt.InvalidTokenError) as exc:
        logger.warning("WebSocket auth failed: %s", exc)
        await ws.close(code=4001, reason="Invalid or expired token")
        return None

    try:
        role = _resolve_role(payload)
    except Exception:
        await ws.close(code=4001, reason="No recognized role")
        return None

    if required_role is not None and role != required_role:
        logger.warning(
            "WebSocket RBAC denied: user=%s role=%s required=%s",
            payload.sub,
            role.value,
            required_role.value,
        )
        await ws.close(code=4003, reason="Insufficient permissions")
        return None

    data_scope = build_data_scope(role, payload.sub)
    return UserContext(
        user_id=payload.sub,
        role=role,
        email=payload.email,
        name=payload.name or payload.preferred_username,
        data_scope=data_scope,
    )


async def run_agent_stream(
    ws: WebSocket,
    graph,
    *,
    thread_id: str,
    session_id: str,
    user_role: str,
    user_id: str,
    user_email: str = "",
    user_name: str = "",
    use_checkpointer: bool,
    messages_fallback: list | None,
) -> None:
    """Run the agent streaming loop over an accepted WebSocket.

    Handles message receive, event streaming, and audit writing.
    Both public chat and borrower chat call this.

    Args:
        ws: The accepted WebSocket connection.
        graph: A compiled LangGraph graph.
        thread_id: The checkpoint thread ID.
        session_id: Session ID for audit + LangFuse correlation.
        user_role: Role string for the agent state.
        user_id: User ID string for the agent state.
        use_checkpointer: Whether checkpoint persistence is active.
        messages_fallback: Mutable list for local message tracking when
            checkpointer is unavailable. Pass ``None`` when using checkpointer.
    """
    from db import get_db

    async def _audit(event_type: str, event_data: dict | None = None) -> None:
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
            logger.warning("Failed to write audit event %s", event_type, exc_info=True)

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

            if use_checkpointer:
                input_messages = [HumanMessage(content=user_text)]
            else:
                messages_fallback.append(HumanMessage(content=user_text))
                input_messages = messages_fallback

            config = {
                **build_langfuse_config(session_id=session_id),
                "configurable": {"thread_id": thread_id},
            }

            try:
                full_response = ""
                async for event in graph.astream_events(
                    {
                        "messages": input_messages,
                        "user_role": user_role,
                        "user_id": user_id,
                        "user_email": user_email,
                        "user_name": user_name,
                    },
                    config=config,
                    version="v2",
                ):
                    kind = event.get("event")
                    node = event.get("metadata", {}).get("langgraph_node")

                    if kind == "on_chat_model_stream" and node in (
                        "agent",
                        "agent_fast",
                        "agent_capable",
                    ):
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
                                    {"shield": "output", "blocked": True},
                                )

                # Without checkpointer, manually track history for this session
                if not use_checkpointer and full_response:
                    messages_fallback.append(AIMessage(content=full_response))

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

    except Exception:
        logger.debug("Client disconnected from chat")
    finally:
        flush_langfuse()
