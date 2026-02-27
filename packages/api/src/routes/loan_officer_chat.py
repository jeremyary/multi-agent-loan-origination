# This project was developed with assistance from AI tools.
"""Authenticated WebSocket chat endpoint for loan officer assistant.

Requires a valid JWT with loan_officer role via ``?token=<jwt>`` query param.
Conversations persist across sessions using deterministic thread IDs
derived from the authenticated user's ID.
"""

import logging
import uuid

from db.enums import UserRole
from fastapi import APIRouter, Depends, WebSocket

from ..agents.registry import get_agent
from ..middleware.auth import CurrentUser, require_roles
from ..services.conversation import ConversationService, get_conversation_service
from ._chat_handler import authenticate_websocket, run_agent_stream

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/loan-officer/chat")
async def loan_officer_chat_websocket(ws: WebSocket):
    """Authenticated WebSocket endpoint for loan officer assistant chat."""
    await ws.accept()

    user = await authenticate_websocket(ws, required_role=UserRole.LOAN_OFFICER)
    if user is None:
        return  # WS closed by authenticate_websocket

    # Resolve checkpointer for conversation persistence
    service = get_conversation_service()
    use_checkpointer = service.is_initialized
    checkpointer = service.checkpointer if use_checkpointer else None

    try:
        graph = get_agent("loan-officer-assistant", checkpointer=checkpointer)
    except Exception:
        logger.exception("Failed to load loan-officer-assistant agent")
        await ws.send_json(
            {"type": "error", "content": "Our chat assistant is temporarily unavailable."}
        )
        await ws.close()
        return

    thread_id = ConversationService.get_thread_id(user.user_id, "loan-officer-assistant")
    session_id = str(uuid.uuid4())

    # LO always uses checkpointer when available; fallback to local list
    messages_fallback: list | None = [] if not use_checkpointer else None

    await run_agent_stream(
        ws,
        graph,
        thread_id=thread_id,
        session_id=session_id,
        user_role=user.role.value,
        user_id=user.user_id,
        user_email=user.email or "",
        user_name=user.name or "",
        use_checkpointer=use_checkpointer,
        messages_fallback=messages_fallback,
    )


@router.get(
    "/loan-officer/conversations/history",
    dependencies=[Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.ADMIN))],
)
async def get_lo_conversation_history(user: CurrentUser) -> dict:
    """Return prior conversation messages for the authenticated loan officer.

    Used by the frontend to render chat history when the chat window opens.
    """
    service = get_conversation_service()
    thread_id = ConversationService.get_thread_id(user.user_id, "loan-officer-assistant")
    messages = await service.get_conversation_history(thread_id)
    return {"data": messages}
