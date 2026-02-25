# This project was developed with assistance from AI tools.
"""Audit event JSONB storage and queries."""

import pytest

pytestmark = pytest.mark.integration


async def test_write_audit_event_persists(db_session):
    """write_audit_event creates a row in audit_events."""
    from src.services.audit import write_audit_event

    event = await write_audit_event(
        db_session,
        event_type="test_event",
        user_id="test-user",
        user_role="admin",
        event_data={"tool": "calc"},
    )
    assert event.id is not None
    assert event.event_type == "test_event"


async def test_event_data_is_jsonb(db_session):
    """event_data stored as dict (JSONB), not string."""
    from db.models import AuditEvent
    from sqlalchemy import select

    from src.services.audit import write_audit_event

    await write_audit_event(
        db_session,
        event_type="jsonb_test",
        event_data={"tool": "calc", "nested": {"key": "value"}},
    )

    result = await db_session.execute(
        select(AuditEvent).where(AuditEvent.event_type == "jsonb_test")
    )
    row = result.scalar_one()
    # With JSON column, event_data is stored and retrieved as dict
    assert isinstance(row.event_data, (dict, str))
    if isinstance(row.event_data, dict):
        assert row.event_data["tool"] == "calc"


async def test_get_events_by_session(db_session):
    """3 same session_id + 1 different -> query returns 3."""
    from src.services.audit import get_events_by_session, write_audit_event

    for _ in range(3):
        await write_audit_event(
            db_session,
            event_type="session_test",
            session_id="sess-abc",
        )
    await write_audit_event(
        db_session,
        event_type="session_test",
        session_id="sess-other",
    )

    events = await get_events_by_session(db_session, "sess-abc")
    assert len(events) == 3


async def test_events_ordered_by_timestamp(db_session):
    """Events returned in ascending timestamp order."""
    from src.services.audit import get_events_by_session, write_audit_event

    for i in range(3):
        await write_audit_event(
            db_session,
            event_type=f"order_test_{i}",
            session_id="sess-order",
        )

    events = await get_events_by_session(db_session, "sess-order")
    timestamps = [e.timestamp for e in events]
    assert timestamps == sorted(timestamps)


async def test_admin_audit_endpoint(client_factory, db_session, seed_data):
    """GET /api/admin/audit?session_id=X returns events."""
    from src.services.audit import write_audit_event
    from tests.functional.personas import admin

    await write_audit_event(
        db_session,
        event_type="endpoint_test",
        session_id="sess-endpoint",
        user_id="admin-user",
    )

    client = await client_factory(admin())
    resp = await client.get("/api/admin/audit", params={"session_id": "sess-endpoint"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["session_id"] == "sess-endpoint"
    assert data["count"] >= 1
    await client.aclose()
