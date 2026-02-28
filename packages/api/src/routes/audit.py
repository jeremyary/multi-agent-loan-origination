# This project was developed with assistance from AI tools.
"""CEO audit trail query and export endpoints (F13, F15)."""

from db import get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import require_roles
from ..schemas.audit import (
    AuditByApplicationResponse,
    AuditByDecisionResponse,
    AuditEventItem,
    AuditSearchResponse,
    DecisionTraceResponse,
)
from ..services.audit import (
    export_events,
    get_decision_trace,
    get_events_by_application,
    get_events_by_decision,
    search_events,
    write_audit_event,
)

router = APIRouter()


def _to_item(evt) -> AuditEventItem:
    return AuditEventItem(
        id=evt.id,
        timestamp=evt.timestamp,
        event_type=evt.event_type,
        user_id=evt.user_id,
        user_role=evt.user_role,
        application_id=evt.application_id,
        decision_id=evt.decision_id,
        event_data=evt.event_data,
    )


@router.get(
    "/application/{application_id}",
    response_model=AuditByApplicationResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def audit_by_application(
    application_id: int,
    session: AsyncSession = Depends(get_db),
) -> AuditByApplicationResponse:
    """Query audit trail by application ID (S-5-F13-01)."""
    events = await get_events_by_application(session, application_id)
    return AuditByApplicationResponse(
        application_id=application_id,
        count=len(events),
        events=[_to_item(e) for e in events],
    )


@router.get(
    "/decision/{decision_id}",
    response_model=AuditByDecisionResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def audit_by_decision(
    decision_id: int,
    session: AsyncSession = Depends(get_db),
) -> AuditByDecisionResponse:
    """Query audit trail by decision ID (S-5-F13-02)."""
    events = await get_events_by_decision(session, decision_id)
    return AuditByDecisionResponse(
        decision_id=decision_id,
        count=len(events),
        events=[_to_item(e) for e in events],
    )


@router.get(
    "/decision/{decision_id}/trace",
    response_model=DecisionTraceResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def decision_trace(
    decision_id: int,
    session: AsyncSession = Depends(get_db),
) -> DecisionTraceResponse:
    """Backward trace from decision to all contributing events (S-5-F13-05)."""
    trace = await get_decision_trace(session, decision_id)
    if trace is None:
        raise HTTPException(status_code=404, detail="Decision not found")
    return DecisionTraceResponse(**trace)


@router.get(
    "/search",
    response_model=AuditSearchResponse,
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO))],
)
async def audit_search(
    days: int | None = Query(default=None, ge=1, le=365, description="Time range in days"),
    event_type: str | None = Query(default=None, description="Filter by event type"),
    limit: int = Query(default=500, ge=1, le=5000, description="Max events to return"),
    session: AsyncSession = Depends(get_db),
) -> AuditSearchResponse:
    """Search audit events by time range and/or event type (S-5-F13-03)."""
    events = await search_events(session, days=days, event_type=event_type, limit=limit)
    return AuditSearchResponse(
        count=len(events),
        events=[_to_item(e) for e in events],
    )


@router.get(
    "/export",
    dependencies=[Depends(require_roles(UserRole.ADMIN, UserRole.CEO, UserRole.UNDERWRITER))],
)
async def audit_export(
    fmt: str = Query(default="json", pattern="^(json|csv)$", description="Export format"),
    application_id: int | None = Query(default=None, description="Filter by application"),
    days: int | None = Query(default=None, ge=1, le=365, description="Time range in days"),
    limit: int = Query(default=10_000, ge=1, le=50_000, description="Max events"),
    session: AsyncSession = Depends(get_db),
) -> Response:
    """Export audit trail as CSV or JSON (S-5-F15-07).

    PII masking is applied by the PIIMaskingMiddleware for CEO role.
    """
    content, media_type = await export_events(
        session,
        fmt=fmt,
        application_id=application_id,
        days=days,
        limit=limit,
    )

    # Log the export event to the audit trail
    await write_audit_event(
        session,
        event_type="data_access",
        event_data={
            "action": "audit_export",
            "format": fmt,
            "application_id": application_id,
            "days": days,
        },
    )
    await session.commit()

    filename = f"audit_export.{fmt}"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
