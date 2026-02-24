# This project was developed with assistance from AI tools.
"""Audit event service.

Writes append-only audit trail entries with session_id for LangFuse trace
correlation (S-1-F18-03). The same session_id used in LangFuse metadata
is written here, enabling cross-lookup between developer-facing traces
and compliance-facing audit logs.
"""

import json
import logging

from db import AuditEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def write_audit_event(
    session: AsyncSession,
    *,
    event_type: str,
    session_id: str | None = None,
    user_id: str | None = None,
    user_role: str | None = None,
    application_id: int | None = None,
    event_data: dict | None = None,
) -> AuditEvent:
    """Write a single audit event.

    Args:
        session: Database session.
        event_type: Event category (e.g. 'tool_invocation', 'safety_block').
        session_id: WebSocket/LangFuse session ID for trace correlation.
        user_id: User who triggered the event.
        user_role: Role at the time of the event.
        application_id: Related application, if any.
        event_data: Arbitrary JSON-serializable event payload.

    Returns:
        The created AuditEvent row.
    """
    audit = AuditEvent(
        event_type=event_type,
        session_id=session_id,
        user_id=user_id,
        user_role=user_role,
        application_id=application_id,
        event_data=json.dumps(event_data) if event_data else None,
    )
    session.add(audit)
    await session.flush()
    return audit


async def get_events_by_session(
    session: AsyncSession,
    session_id: str,
) -> list[AuditEvent]:
    """Return all audit events for a given session_id.

    This is the compliance-side query for trace-audit correlation:
    given a session_id from LangFuse, retrieve all audit events.
    """
    stmt = (
        select(AuditEvent)
        .where(AuditEvent.session_id == session_id)
        .order_by(AuditEvent.timestamp.asc())
    )
    result = await session.execute(stmt)
    return list(result.scalars().all())
