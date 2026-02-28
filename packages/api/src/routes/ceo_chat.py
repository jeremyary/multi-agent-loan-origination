# This project was developed with assistance from AI tools.
"""Authenticated WebSocket chat endpoint for CEO executive assistant.

Requires a valid JWT with CEO role via ``?token=<jwt>`` query param.
Conversations persist across sessions using deterministic thread IDs
derived from the authenticated user's ID.
"""

from db.enums import UserRole

from ._chat_handler import create_authenticated_chat_router

router = create_authenticated_chat_router(
    role=UserRole.CEO,
    agent_name="ceo-assistant",
    ws_path="/ceo/chat",
    history_path="/ceo/conversations/history",
)
