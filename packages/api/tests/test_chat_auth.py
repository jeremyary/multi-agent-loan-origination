# This project was developed with assistance from AI tools.
"""Tests for chat authentication and route factory.

Validates that WebSocket chat routes are created correctly and that the
ConversationHistoryResponse schema works as expected.
"""

from db.enums import UserRole
from fastapi import APIRouter

from src.routes._chat_handler import create_authenticated_chat_router
from src.schemas.conversation import ConversationHistoryResponse


def test_chat_route_factory_creates_router():
    """create_authenticated_chat_router returns an APIRouter."""
    router = create_authenticated_chat_router(
        role=UserRole.BORROWER,
        agent_name="borrower-assistant",
        ws_path="/borrower/chat",
        history_path="/borrower/conversations/history",
    )
    assert isinstance(router, APIRouter)


def test_conversation_history_response_schema():
    """ConversationHistoryResponse validates correctly."""
    response = ConversationHistoryResponse(
        data=[
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
    )
    assert len(response.data) == 2
    assert response.data[0].role == "user"
    assert response.data[0].content == "Hello"
    assert response.data[1].role == "assistant"
    assert response.data[1].content == "Hi there!"


def test_conversation_history_response_empty():
    """ConversationHistoryResponse accepts empty message list."""
    response = ConversationHistoryResponse(data=[])
    assert len(response.data) == 0
