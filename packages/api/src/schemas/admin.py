# This project was developed with assistance from AI tools.
"""Pydantic response models for admin endpoints."""

from datetime import datetime

from pydantic import BaseModel


class SeedResponse(BaseModel):
    """Response for POST /api/admin/seed."""

    status: str
    seeded_at: datetime | None = None
    config_hash: str | None = None
    borrowers: int | None = None
    active_applications: int | None = None
    historical_loans: int | None = None
    hmda_demographics: int | None = None
    kb_documents: int | None = None
    kb_chunks: int | None = None


class SeedSummary(BaseModel):
    """Breakdown of seeded data counts."""

    borrowers: int = 0
    active_applications: int = 0
    historical_loans: int = 0
    hmda_demographics: int = 0
    kb_documents: int = 0
    kb_chunks: int = 0


class SeedStatusResponse(BaseModel):
    """Response for GET /api/admin/seed/status."""

    seeded: bool
    seeded_at: datetime | None = None
    config_hash: str | None = None
    summary: SeedSummary | None = None
