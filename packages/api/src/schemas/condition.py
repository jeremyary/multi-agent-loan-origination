# This project was developed with assistance from AI tools.
"""Schemas for condition endpoints."""

from datetime import datetime

from pydantic import BaseModel

from . import Pagination


class ConditionItem(BaseModel):
    """Single condition in a list response."""

    id: int
    description: str
    severity: str | None = None
    status: str | None = None
    response_text: str | None = None
    issued_by: str | None = None
    cleared_by: str | None = None
    due_date: datetime | None = None
    iteration_count: int = 0
    waiver_rationale: str | None = None
    created_at: datetime | None = None


class ConditionListResponse(BaseModel):
    """Response for GET /applications/{id}/conditions."""

    data: list[ConditionItem]
    pagination: Pagination


class ConditionResponse(BaseModel):
    """Response for a single condition after an update."""

    data: ConditionItem


class ConditionRespondRequest(BaseModel):
    """Request body for responding to a condition with text."""

    response_text: str
