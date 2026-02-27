# This project was developed with assistance from AI tools.
"""Urgency indicator schemas for pipeline management."""

import enum

from pydantic import BaseModel


class UrgencyLevel(enum.StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    NORMAL = "normal"


class UrgencyIndicator(BaseModel):
    """Urgency assessment for a single application."""

    level: UrgencyLevel
    factors: list[str]
    days_in_stage: int
    expected_stage_days: int
