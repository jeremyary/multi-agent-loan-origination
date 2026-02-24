# This project was developed with assistance from AI tools.
"""Admin endpoints for demo data seeding."""

from db import get_compliance_db, get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..services.seed.seeder import get_seed_status, seed_demo_data

router = APIRouter()


@router.post(
    "/seed",
    status_code=status.HTTP_200_OK,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def seed_data(
    force: bool = False,
    session: AsyncSession = Depends(get_db),
    compliance_session: AsyncSession = Depends(get_compliance_db),
) -> dict:
    """Seed demo data. Pass force=true to re-seed.

    Simulated for demonstration purposes -- not real financial data.
    """
    try:
        return await seed_demo_data(session, compliance_session, force=force)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc


@router.get(
    "/seed/status",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def seed_status(
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Check if demo data has been seeded."""
    return await get_seed_status(session)
