# This project was developed with assistance from AI tools.
"""Authenticated WebSocket chat endpoint for loan officer assistant.

Requires a valid JWT with loan_officer role via ``?token=<jwt>`` query param.
Conversations persist across sessions using deterministic thread IDs
derived from the authenticated user's ID.
"""

from db.enums import UserRole

from ._chat_handler import create_authenticated_chat_router

router = create_authenticated_chat_router(
    role=UserRole.LOAN_OFFICER,
    agent_name="loan-officer-assistant",
    ws_path="/loan-officer/chat",
    history_path="/loan-officer/conversations/history",
)
