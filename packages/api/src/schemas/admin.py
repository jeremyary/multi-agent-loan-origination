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


class SeedStatusResponse(BaseModel):
    """Response for GET /api/admin/seed/status."""

    seeded: bool
    seeded_at: datetime | None = None
    config_hash: str | None = None
    summary: dict | None = None
