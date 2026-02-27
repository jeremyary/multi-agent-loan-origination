# This project was developed with assistance from AI tools.
"""Admin endpoints for demo data seeding and audit trail queries."""

from db import get_compliance_db, get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..schemas.admin import (
    AuditChainVerifyResponse,
    AuditEventItem,
    AuditEventsResponse,
    SeedResponse,
    SeedStatusResponse,
)
from ..services.audit import get_events_by_session, verify_audit_chain
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


@router.get(
    "/audit",
    response_model=AuditEventsResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def get_audit_events(
    session_id: str = Query(..., description="LangFuse/WebSocket session ID"),
    session: AsyncSession = Depends(get_db),
) -> AuditEventsResponse:
    """Query audit events by session_id for trace-audit correlation."""
    events = await get_events_by_session(session, session_id)
    return AuditEventsResponse(
        session_id=session_id,
        count=len(events),
        events=[
            AuditEventItem(
                id=e.id,
                timestamp=e.timestamp,
                event_type=e.event_type,
                user_id=e.user_id,
                user_role=e.user_role,
                application_id=e.application_id,
                event_data=e.event_data,
            )
            for e in events
        ],
    )


@router.get(
    "/audit/verify",
    response_model=AuditChainVerifyResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN))],
)
async def verify_audit(
    session: AsyncSession = Depends(get_db),
) -> AuditChainVerifyResponse:
    """Verify audit trail hash chain integrity."""
    result = await verify_audit_chain(session)
    return AuditChainVerifyResponse(**result)
