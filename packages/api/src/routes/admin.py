# This project was developed with assistance from AI tools.
"""Admin endpoints for demo data seeding."""

from db import get_compliance_db, get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..schemas.admin import SeedResponse, SeedStatusResponse
from ..services.seed.seeder import get_seed_status, seed_demo_data

router = APIRouter()


@router.post(
    "/seed",
    response_model=SeedResponse,
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def seed_data(
    force: bool = False,
    session: AsyncSession = Depends(get_db),
    compliance_session: AsyncSession = Depends(get_compliance_db),
) -> SeedResponse:
    """Seed demo data. Pass force=true to re-seed.

    Simulated for demonstration purposes -- not real financial data.
    """
    try:
        result = await seed_demo_data(session, compliance_session, force=force)
        return SeedResponse(**result)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/seed/status",
    response_model=SeedStatusResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def seed_status(
    session: AsyncSession = Depends(get_db),
) -> SeedStatusResponse:
    """Check if demo data has been seeded."""
    result = await get_seed_status(session)
    return SeedStatusResponse(**result)
