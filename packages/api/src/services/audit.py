# This project was developed with assistance from AI tools.
"""Audit event service.

Writes append-only audit trail entries with SHA-256 hash chain for tamper
evidence (S-2-F15-04) and PostgreSQL advisory lock for serial hash
computation (S-2-F15-05).  Session_id enables LangFuse trace correlation
(S-1-F18-03).
"""

import hashlib
import json
import logging

from db import AuditEvent
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

# Fixed advisory lock key for audit trail serialization.
# Only audit event inserts are serialized; other DB operations are unaffected.
AUDIT_LOCK_KEY = 900_001


def _compute_hash(event_id: int, timestamp: str, event_data: dict | None) -> str:
    """Compute SHA-256 hash of an audit event's key fields."""
    payload = f"{event_id}|{timestamp}|{json.dumps(event_data, sort_keys=True, default=str)}"
    return hashlib.sha256(payload.encode()).hexdigest()


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
    """Write a single audit event with hash chain linkage.

    Acquires a PostgreSQL advisory lock to serialize hash computation,
    then computes prev_hash from the most recent event.

    Args:
        session: Database session.
        event_type: Event category (e.g. 'tool_invocation', 'safety_block').
        session_id: WebSocket/LangFuse session ID for trace correlation.
        user_id: User who triggered the event.
        user_role: Role at the time of the event.
        application_id: Related application, if any.
        event_data: Arbitrary JSON-serializable event payload.

    Returns:
        The created AuditEvent row (with prev_hash set).
    """
    # Advisory lock serializes hash chain computation across concurrent writers.
    # Released automatically when the transaction commits or rolls back.
    await session.execute(text(f"SELECT pg_advisory_xact_lock({AUDIT_LOCK_KEY})"))

    # Fetch the most recent event for hash chain linkage.
    latest_stmt = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(1)
    result = await session.execute(latest_stmt)
    prev_event = result.scalar_one_or_none()

    if prev_event is not None:
        prev_hash = _compute_hash(prev_event.id, str(prev_event.timestamp), prev_event.event_data)
    else:
        prev_hash = "genesis"

    audit = AuditEvent(
        event_type=event_type,
        session_id=session_id,
        user_id=user_id,
        user_role=user_role,
        application_id=application_id,
        event_data=event_data,
        prev_hash=prev_hash,
    )
    session.add(audit)
    await session.flush()
    return audit


async def verify_audit_chain(session: AsyncSession) -> dict:
    """Verify the integrity of the audit event hash chain.

    Walks all events in ID order, recomputes each expected prev_hash,
    and compares against the stored value.

    Returns:
        {"status": "OK", "events_checked": N} on success, or
        {"status": "TAMPERED", "first_break_id": id, "events_checked": N}
        if a mismatch is found.
    """
    stmt = select(AuditEvent).order_by(AuditEvent.id.asc())
    result = await session.execute(stmt)
    events = list(result.scalars().all())

    if not events:
        return {"status": "OK", "events_checked": 0}

    for i, event in enumerate(events):
        if i == 0:
            expected = "genesis"
        else:
            prev = events[i - 1]
            expected = _compute_hash(prev.id, str(prev.timestamp), prev.event_data)

        if event.prev_hash != expected:
            return {
                "status": "TAMPERED",
                "first_break_id": event.id,
                "events_checked": i + 1,
            }

    return {"status": "OK", "events_checked": len(events)}


async def get_audit_chain_length(session: AsyncSession) -> int:
    """Return the total number of audit events."""
    result = await session.execute(select(func.count(AuditEvent.id)))
    return result.scalar_one()


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
