# This project was developed with assistance from AI tools.
"""Pydantic response models for admin endpoints."""

from pydantic import BaseModel


class AuditEventItem(BaseModel):
    """Single audit event in a query response."""

    id: int
    timestamp: str
    event_type: str
    user_id: str | None = None
    user_role: str | None = None
    application_id: int | None = None
    event_data: dict | str | None = None


class AuditEventsResponse(BaseModel):
    """Response for GET /api/admin/audit."""

    session_id: str
    count: int
    events: list[AuditEventItem]


class AuditChainVerifyResponse(BaseModel):
    """Response for GET /api/admin/audit/verify."""

    status: str
    events_checked: int
    first_break_id: int | None = None


class SeedResponse(BaseModel):
    """Response for POST /api/admin/seed."""

    status: str
    seeded_at: str | None = None
    config_hash: str | None = None
    borrowers: int | None = None
    active_applications: int | None = None
    historical_loans: int | None = None
    hmda_demographics: int | None = None


class SeedStatusResponse(BaseModel):
    """Response for GET /api/admin/seed/status."""

    seeded: bool
    seeded_at: str | None = None
    config_hash: str | None = None
    summary: dict | None = None
