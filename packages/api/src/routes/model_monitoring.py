# This project was developed with assistance from AI tools.
"""Model monitoring endpoints for CEO dashboard (F39)."""

import httpx
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query

from ..middleware.auth import require_roles
from ..schemas.model_monitoring import (
    ErrorMetrics,
    LatencyMetrics,
    ModelMonitoringSummary,
    RoutingDistribution,
    TokenUsage,
)
from ..services.model_monitoring import (
    get_model_monitoring_summary,
)

router = APIRouter()

_HOURS_QUERY = Query(default=24, ge=1, le=2160, description="Time range in hours (max 90 days)")
_MODEL_QUERY = Query(default=None, description="Filter by model name")


async def _safe_summary(hours: int, model: str | None) -> ModelMonitoringSummary:
    """Fetch summary with error handling for LangFuse connectivity issues."""
    try:
        return await get_model_monitoring_summary(hours=hours, model=model)
    except (httpx.HTTPStatusError, httpx.RequestError) as exc:
        raise HTTPException(
            status_code=503,
            detail=f"LangFuse unavailable: {exc}",
        ) from exc


@router.get(
    "/model-monitoring",
    response_model=ModelMonitoringSummary,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def model_monitoring_summary(
    hours: int = _HOURS_QUERY,
    model: str | None = _MODEL_QUERY,
) -> ModelMonitoringSummary:
    """Full model monitoring summary: latency, tokens, errors, and routing distribution."""
    return await _safe_summary(hours, model)


@router.get(
    "/model-monitoring/latency",
    response_model=LatencyMetrics,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def model_monitoring_latency(
    hours: int = _HOURS_QUERY,
    model: str | None = _MODEL_QUERY,
) -> LatencyMetrics:
    """Model latency percentiles (p50, p95, p99) with trend and per-model breakdown."""
    summary = await _safe_summary(hours, model)
    if summary.latency is None:
        raise HTTPException(status_code=503, detail="LangFuse not configured")
    return summary.latency


@router.get(
    "/model-monitoring/tokens",
    response_model=TokenUsage,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def model_monitoring_tokens(
    hours: int = _HOURS_QUERY,
    model: str | None = _MODEL_QUERY,
) -> TokenUsage:
    """Token usage totals with trend and per-model breakdown."""
    summary = await _safe_summary(hours, model)
    if summary.token_usage is None:
        raise HTTPException(status_code=503, detail="LangFuse not configured")
    return summary.token_usage


@router.get(
    "/model-monitoring/errors",
    response_model=ErrorMetrics,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def model_monitoring_errors(
    hours: int = _HOURS_QUERY,
    model: str | None = _MODEL_QUERY,
) -> ErrorMetrics:
    """Error rate metrics with top error types and trend."""
    summary = await _safe_summary(hours, model)
    if summary.errors is None:
        raise HTTPException(status_code=503, detail="LangFuse not configured")
    return summary.errors


@router.get(
    "/model-monitoring/routing",
    response_model=RoutingDistribution,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def model_monitoring_routing(
    hours: int = _HOURS_QUERY,
    model: str | None = _MODEL_QUERY,
) -> RoutingDistribution:
    """Model routing distribution across all models."""
    summary = await _safe_summary(hours, model)
    if summary.routing is None:
        raise HTTPException(status_code=503, detail="LangFuse not configured")
    return summary.routing
