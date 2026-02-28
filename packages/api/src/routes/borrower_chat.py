# This project was developed with assistance from AI tools.
"""Authenticated WebSocket chat endpoint for borrower assistant.

Requires a valid JWT with borrower role via ``?token=<jwt>`` query param.
Conversations persist across sessions using deterministic thread IDs
derived from the authenticated user's ID.
"""

from db.enums import UserRole

from ._chat_handler import create_authenticated_chat_router

router = create_authenticated_chat_router(
    role=UserRole.BORROWER,
    agent_name="borrower-assistant",
    ws_path="/borrower/chat",
    history_path="/borrower/conversations/history",
)
