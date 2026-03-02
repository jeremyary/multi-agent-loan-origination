# This project was developed with assistance from AI tools.
"""Pydantic response models for rate lock endpoints."""

from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel


class RateLockStatus(StrEnum):
    """Possible states for a rate lock."""

    ACTIVE = "active"
    EXPIRED = "expired"
    NONE = "none"


class RateLockResponse(BaseModel):
    """Response for GET /api/applications/{id}/rate-lock."""

    application_id: int
    status: RateLockStatus
    locked_rate: float | None = None
    lock_date: datetime | None = None
    expiration_date: datetime | None = None
    days_remaining: int | None = None
    is_urgent: bool | None = None
