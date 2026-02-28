# This project was developed with assistance from AI tools.
"""Audit hash chain + advisory lock tests (S-2-F15-04, F15-05).

Verifies SHA-256 hash chain computation, genesis sentinel, tamper
detection via verify_audit_chain, and the verification endpoint.

Tests rely on db_session's savepoint rollback for isolation -- no
separate TRUNCATE fixture needed (which would deadlock against the
open session-scoped transaction).
"""

import pytest
from sqlalchemy import text

from src.services.audit import _compute_hash, verify_audit_chain, write_audit_event

pytestmark = pytest.mark.integration


async def test_first_event_has_genesis_hash(db_session):
    """First audit event in empty table gets prev_hash='genesis'."""
    event = await write_audit_event(db_session, event_type="genesis_test", user_id="test")
    assert event.prev_hash == "genesis"


async def test_second_event_chains_from_first(db_session):
    """Second event's prev_hash is SHA-256 of first event's fields."""
    first = await write_audit_event(
        db_session, event_type="chain_first", user_id="test", event_data={"step": 1}
    )
    second = await write_audit_event(
        db_session, event_type="chain_second", user_id="test", event_data={"step": 2}
    )

    expected = _compute_hash(
        first.id,
        str(first.timestamp),
        first.event_type,
        first.user_id,
        first.user_role,
        first.application_id,
        first.session_id,
        first.event_data,
    )
    assert second.prev_hash == expected
    assert second.prev_hash != "genesis"


async def test_three_event_chain(db_session):
    """Three events form a valid chain: genesis -> hash(e1) -> hash(e2)."""
    e1 = await write_audit_event(db_session, event_type="e1", event_data={"n": 1})
    e2 = await write_audit_event(db_session, event_type="e2", event_data={"n": 2})
    e3 = await write_audit_event(db_session, event_type="e3", event_data={"n": 3})

    assert e1.prev_hash == "genesis"
    assert e2.prev_hash == _compute_hash(
        e1.id,
        str(e1.timestamp),
        e1.event_type,
        e1.user_id,
        e1.user_role,
        e1.application_id,
        e1.session_id,
        e1.event_data,
    )
    assert e3.prev_hash == _compute_hash(
        e2.id,
        str(e2.timestamp),
        e2.event_type,
        e2.user_id,
        e2.user_role,
        e2.application_id,
        e2.session_id,
        e2.event_data,
    )


async def test_verify_chain_ok(db_session):
    """verify_audit_chain returns OK for a valid chain."""
    for i in range(5):
        await write_audit_event(db_session, event_type=f"verify_{i}", event_data={"i": i})

    result = await verify_audit_chain(db_session)
    assert result["status"] == "OK"
    assert result["events_checked"] == 5


async def test_verify_chain_empty(db_session):
    """verify_audit_chain returns OK with 0 events on empty table."""
    result = await verify_audit_chain(db_session)
    assert result["status"] == "OK"
    assert result["events_checked"] == 0


async def test_verify_chain_detects_tamper(db_session):
    """verify_audit_chain detects a broken chain after direct data tampering."""
    events = []
    for i in range(3):
        e = await write_audit_event(db_session, event_type=f"tamper_{i}", event_data={"i": i})
        events.append(e)

    result = await verify_audit_chain(db_session)
    assert result["status"] == "OK"

    # Tamper: temporarily disable trigger, modify event_data on first event
    conn = await db_session.connection()
    await conn.execute(text("ALTER TABLE audit_events DISABLE TRIGGER audit_events_no_update"))
    await db_session.execute(
        text("UPDATE audit_events SET event_data = cast(:data as jsonb) WHERE id = :id").bindparams(
            data='{"i": "TAMPERED"}', id=events[0].id
        )
    )
    await conn.execute(text("ALTER TABLE audit_events ENABLE TRIGGER audit_events_no_update"))

    db_session.expire_all()

    result = await verify_audit_chain(db_session)
    assert result["status"] == "TAMPERED"
    assert result["first_break_id"] == events[1].id
    assert result["events_checked"] == 2


async def test_verify_endpoint(client_factory, db_session, seed_data):
    """GET /api/audit/verify returns chain status."""
    from tests.functional.personas import admin

    await write_audit_event(db_session, event_type="endpoint_verify_test", user_id="admin")

    client = await client_factory(admin())
    resp = await client.get("/api/audit/verify")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "OK"
    assert data["events_checked"] >= 1
    await client.aclose()


async def test_hash_is_deterministic():
    """_compute_hash produces consistent output for same inputs."""
    h1 = _compute_hash(
        1,
        "2026-01-01T00:00:00+00:00",
        "test_type",
        "user1",
        "borrower",
        100,
        "sess1",
        {"key": "value"},
    )
    h2 = _compute_hash(
        1,
        "2026-01-01T00:00:00+00:00",
        "test_type",
        "user1",
        "borrower",
        100,
        "sess1",
        {"key": "value"},
    )
    assert h1 == h2
    assert len(h1) == 64


async def test_hash_changes_with_different_data():
    """_compute_hash produces different output for different inputs."""
    h1 = _compute_hash(
        1, "2026-01-01T00:00:00+00:00", "test_type", "user1", "borrower", 100, "sess1", {"key": "a"}
    )
    h2 = _compute_hash(
        1, "2026-01-01T00:00:00+00:00", "test_type", "user1", "borrower", 100, "sess1", {"key": "b"}
    )
    assert h1 != h2
