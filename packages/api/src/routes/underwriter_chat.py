# This project was developed with assistance from AI tools.
"""Authenticated WebSocket chat endpoint for underwriter assistant.

Requires a valid JWT with underwriter role via ``?token=<jwt>`` query param.
Conversations persist across sessions using deterministic thread IDs
derived from the authenticated user's ID.
"""

from db.enums import UserRole

from ._chat_handler import create_authenticated_chat_router

router = create_authenticated_chat_router(
    role=UserRole.UNDERWRITER,
    agent_name="underwriter-assistant",
    ws_path="/underwriter/chat",
    history_path="/underwriter/conversations/history",
)
