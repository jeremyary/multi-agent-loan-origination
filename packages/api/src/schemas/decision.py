# This project was developed with assistance from AI tools.
"""Schemas for decision endpoints."""

from datetime import datetime

from pydantic import BaseModel

from . import Pagination


class DecisionItem(BaseModel):
    """Single underwriting decision."""

    id: int
    application_id: int
    decision_type: str
    rationale: str | None = None
    ai_recommendation: str | None = None
    ai_agreement: bool | None = None
    override_rationale: str | None = None
    denial_reasons: list[str] | None = None
    credit_score_used: int | None = None
    credit_score_source: str | None = None
    contributing_factors: str | None = None
    decided_by: str | None = None
    created_at: datetime | None = None


class DecisionResponse(BaseModel):
    """Response for a single decision."""

    data: DecisionItem


class DecisionListResponse(BaseModel):
    """Response for listing decisions."""

    data: list[DecisionItem]
    pagination: Pagination
