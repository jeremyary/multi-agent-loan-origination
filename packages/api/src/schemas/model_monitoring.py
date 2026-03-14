# This project was developed with assistance from AI tools.
"""Pydantic schemas for model monitoring metrics (F39)."""

from datetime import datetime

from pydantic import BaseModel, Field


class LatencyTrendPoint(BaseModel):
    """Latency at a single point in time."""

    timestamp: datetime
    p50_ms: float
    p95_ms: float
    p99_ms: float


class ModelLatencyBreakdown(BaseModel):
    """Latency percentiles for a single model."""

    model: str
    p50_ms: float
    p95_ms: float
    p99_ms: float
    call_count: int


class LatencyMetrics(BaseModel):
    """Latency percentiles across all models with trend and per-model breakdown."""

    p50_ms: float = Field(..., description="50th percentile latency in milliseconds")
    p95_ms: float = Field(..., description="95th percentile latency in milliseconds")
    p99_ms: float = Field(..., description="99th percentile latency in milliseconds")
    trend: list[LatencyTrendPoint] = Field(
        default_factory=list, description="Hourly latency trend points"
    )
    by_model: list[ModelLatencyBreakdown] = Field(
        default_factory=list, description="Per-model latency breakdown"
    )


class ModelTokenBreakdown(BaseModel):
    """Token usage for a single model."""

    model: str
    input_tokens: int
    output_tokens: int
    total_tokens: int
    call_count: int


class TokenTrendPoint(BaseModel):
    """Token usage at a single point in time."""

    timestamp: datetime
    input_tokens: int
    output_tokens: int
    total_tokens: int


class TokenUsage(BaseModel):
    """Token usage totals with trend and per-model breakdown."""

    input_tokens: int = Field(..., description="Total input tokens consumed")
    output_tokens: int = Field(..., description="Total output tokens generated")
    total_tokens: int = Field(..., description="Total tokens (input + output)")
    trend: list[TokenTrendPoint] = Field(
        default_factory=list, description="Hourly token usage trend"
    )
    by_model: list[ModelTokenBreakdown] = Field(
        default_factory=list, description="Per-model token breakdown"
    )


class ErrorTypeCount(BaseModel):
    """Count for a single error type."""

    error_type: str
    count: int


class ErrorTrendPoint(BaseModel):
    """Error rate at a single point in time."""

    timestamp: datetime
    total_calls: int
    error_count: int
    error_rate: float


class ErrorMetrics(BaseModel):
    """Error rate metrics with top error types and trend."""

    total_calls: int = Field(..., description="Total inference calls in the time range")
    error_count: int = Field(..., description="Number of calls that errored")
    error_rate: float = Field(..., description="Error rate as a percentage")
    top_errors: list[ErrorTypeCount] = Field(
        default_factory=list, description="Most frequent error types"
    )
    trend: list[ErrorTrendPoint] = Field(
        default_factory=list, description="Hourly error rate trend"
    )


class ModelRoutingEntry(BaseModel):
    """Routing distribution for a single model."""

    model: str
    call_count: int
    percentage: float = Field(..., description="Percentage of total calls routed to this model")


class RoutingDistribution(BaseModel):
    """Model routing distribution across all models."""

    models: list[ModelRoutingEntry] = Field(
        default_factory=list, description="Per-model call counts and percentages"
    )
    total_calls: int = Field(..., description="Total calls across all models")


class ModelMonitoringSummary(BaseModel):
    """Top-level response combining all monitoring panels."""

    mlflow_available: bool = Field(..., description="Whether MLFlow is configured and reachable")
    latency: LatencyMetrics | None = None
    token_usage: TokenUsage | None = None
    errors: ErrorMetrics | None = None
    routing: RoutingDistribution | None = None
    time_range_hours: int = Field(..., description="Requested time range in hours")
    computed_at: datetime
