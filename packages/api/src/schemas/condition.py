# This project was developed with assistance from AI tools.
"""Schemas for condition endpoints."""

from pydantic import BaseModel


class ConditionItem(BaseModel):
    """Single condition in a list response."""

    id: int
    description: str
    severity: str | None = None
    status: str | None = None
    response_text: str | None = None
    issued_by: str | None = None
    created_at: str | None = None


class ConditionListResponse(BaseModel):
    """Response for GET /applications/{id}/conditions."""

    data: list[ConditionItem]
    count: int


class ConditionRespondRequest(BaseModel):
    """Request body for responding to a condition with text."""

    response_text: str
