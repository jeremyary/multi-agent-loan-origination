# This project was developed with assistance from AI tools.
"""Pydantic response schemas for audit trail endpoints."""

from datetime import datetime

from pydantic import BaseModel, Field


class AuditEventItem(BaseModel):
    """Single audit event in a query response."""

    id: int
    timestamp: datetime
    event_type: str
    user_id: str | None = None
    user_role: str | None = None
    application_id: int | None = None
    decision_id: int | None = None
    event_data: dict | str | None = None


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


class DecisionTraceResponse(BaseModel):
    """Structured backward trace from a decision to all contributing events."""

    decision_id: int
    application_id: int
    decision_type: str | None = None
    rationale: str | None = None
    ai_recommendation: str | None = None
    ai_agreement: bool | None = None
    override_rationale: str | None = None
    denial_reasons: list | dict | None = None
    decided_by: str | None = None
    events_by_type: dict[str, list] = Field(
        default_factory=dict,
        description="Audit events grouped by event_type",
    )
    total_events: int = 0
