# This project was developed with assistance from AI tools.
"""Analytics endpoints for CEO executive dashboard (F12)."""

from db import get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..schemas.analytics import DenialTrends, PipelineSummary
from ..services.analytics import get_denial_trends, get_pipeline_summary

router = APIRouter()


@router.get(
    "/pipeline",
    response_model=PipelineSummary,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def pipeline_summary(
    days: int = Query(default=90, ge=1, le=365, description="Time range in days"),
    session: AsyncSession = Depends(get_db),
) -> PipelineSummary:
    """Pipeline summary: volume, stage distribution, turn times, pull-through rate."""
    return await get_pipeline_summary(session, days=days)


@router.get(
    "/denial-trends",
    response_model=DenialTrends,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def denial_trends(
    days: int = Query(default=90, ge=1, le=365, description="Time range in days"),
    product: str | None = Query(default=None, description="Filter by loan type"),
    session: AsyncSession = Depends(get_db),
) -> DenialTrends:
    """Denial rate trends: overall rate, time-based trend, top reasons by product."""
    try:
        return await get_denial_trends(session, days=days, product=product)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
