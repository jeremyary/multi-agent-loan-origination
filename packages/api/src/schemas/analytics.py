# This project was developed with assistance from AI tools.
"""Analytics response schemas for CEO executive dashboard."""

from datetime import datetime

from pydantic import BaseModel, Field


class StageCount(BaseModel):
    """Application count for a single stage."""

    stage: str
    count: int


class StageTurnTime(BaseModel):
    """Average turn time for a stage transition."""

    from_stage: str
    to_stage: str
    avg_days: float = Field(..., description="Average days in the from_stage before transitioning")
    sample_size: int = Field(..., description="Number of applications in the calculation")


class PipelineSummary(BaseModel):
    """Pipeline health metrics: volume, stage distribution, turn times."""

    total_applications: int
    by_stage: list[StageCount]
    pull_through_rate: float = Field(
        ..., description="Percentage of applications reaching closed stage"
    )
    avg_days_to_close: float | None = Field(
        None, description="Average days from creation to closed stage"
    )
    turn_times: list[StageTurnTime]
    time_range_days: int
    computed_at: datetime


class DenialReason(BaseModel):
    """A single denial reason with count."""

    reason: str
    count: int
    percentage: float


class DenialTrendPoint(BaseModel):
    """Denial rate at a single point in time."""

    period: str = Field(..., description="Period label, e.g. '2026-02' or 'Week 8'")
    denial_rate: float
    denial_count: int
    total_decided: int


class DenialTrends(BaseModel):
    """Denial rate metrics: overall rate, trends, top reasons."""

    overall_denial_rate: float
    total_decisions: int
    total_denials: int
    trend: list[DenialTrendPoint]
    top_reasons: list[DenialReason]
    by_product: dict[str, float] | None = Field(
        None, description="Denial rate per product type, when product filter is not applied"
    )
    time_range_days: int
    computed_at: datetime
