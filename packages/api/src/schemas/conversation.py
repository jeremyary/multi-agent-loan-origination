# This project was developed with assistance from AI tools.
"""Conversation-related response schemas."""

from pydantic import BaseModel, Field


class ConversationMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(..., description="Message role: 'user' or 'assistant'")
    content: str = Field(..., description="Message text content")


class ConversationHistoryResponse(BaseModel):
    """Response for conversation history endpoints."""

    data: list[ConversationMessage] = Field(
        default_factory=list,
        description="List of conversation messages in chronological order",
    )
