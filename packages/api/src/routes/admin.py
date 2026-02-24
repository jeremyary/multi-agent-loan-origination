# This project was developed with assistance from AI tools.
"""Admin endpoints for demo data seeding and audit trail queries."""

from db import get_compliance_db, get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..services.audit import get_events_by_session
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


@router.get(
    "/audit",
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def get_audit_events(
    session_id: str = Query(..., description="LangFuse/WebSocket session ID"),
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Query audit events by session_id for trace-audit correlation."""
    events = await get_events_by_session(session, session_id)
    return {
        "session_id": session_id,
        "count": len(events),
        "events": [
            {
                "id": e.id,
                "timestamp": str(e.timestamp),
                "event_type": e.event_type,
                "user_id": e.user_id,
                "user_role": e.user_role,
                "application_id": e.application_id,
                "event_data": e.event_data,
            }
            for e in events
        ],
    }
