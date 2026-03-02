# This project was developed with assistance from AI tools.
"""Pydantic response schemas for audit trail endpoints."""

import json
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator


class AuditEventItem(BaseModel):
    """Single audit event in a query response."""

    id: int
    timestamp: datetime
    event_type: str
    user_id: str | None = None
    user_role: str | None = None
    application_id: int | None = None
    decision_id: int | None = None
    event_data: dict[str, Any] | None = None

    @field_validator("event_data", mode="before")
    @classmethod
    def _parse_event_data(cls, v: Any) -> dict[str, Any] | None:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {"raw": v}
        return v


class AuditBySessionResponse(BaseModel):
    """Response for audit trail query by session ID."""

    session_id: str
    count: int
    events: list[AuditEventItem]


class AuditByApplicationResponse(BaseModel):
    """Response for audit trail query by application ID."""

    application_id: int
    count: int
    events: list[AuditEventItem]


class AuditByDecisionResponse(BaseModel):
    """Response for audit trail query by decision ID."""

    decision_id: int
    count: int
    events: list[AuditEventItem]


class AuditSearchResponse(BaseModel):
    """Response for audit trail search queries."""

    count: int
    events: list[AuditEventItem]


class AuditChainVerifyResponse(BaseModel):
    """Response for audit hash chain verification."""

    status: str
    events_checked: int
    first_break_id: int | None = None


class DecisionTraceEvent(BaseModel):
    """Simplified audit event used inside a decision trace."""

    id: int
    timestamp: str | None = None
    user_id: str | None = None
    user_role: str | None = None
    event_data: dict[str, Any] | None = None

    @field_validator("event_data", mode="before")
    @classmethod
    def _parse_event_data(cls, v: Any) -> dict[str, Any] | None:
        if isinstance(v, str):
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                return {"raw": v}
        return v


class DecisionTraceResponse(BaseModel):
    """Structured backward trace from a decision to all contributing events."""

    decision_id: int
    application_id: int
    decision_type: str | None = None
    rationale: str | None = None
    ai_recommendation: str | None = None
    ai_agreement: bool | None = None
    override_rationale: str | None = None
    denial_reasons: list[str] | None = None
    decided_by: str | None = None
    events_by_type: dict[str, list[DecisionTraceEvent]] = Field(
        default_factory=dict,
        description="Audit events grouped by event_type",
    )
    total_events: int = 0
