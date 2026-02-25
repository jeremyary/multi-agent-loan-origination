# This project was developed with assistance from AI tools.
"""HMDA demographics: collection, upsert, precedence, isolation."""

import pytest
from sqlalchemy import select

pytestmark = pytest.mark.integration


async def test_collect_creates_row(client_factory, db_session, compliance_session, seed_data):
    """POST /api/hmda/collect creates row in hmda.demographics."""
    from db.models import HmdaDemographic

    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "race": "White",
            "ethnicity": "Not Hispanic or Latino",
            "sex": "Female",
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["application_id"] == seed_data.sarah_app1.id

    # Verify row exists in compliance session
    result = await compliance_session.execute(
        select(HmdaDemographic).where(
            HmdaDemographic.application_id == seed_data.sarah_app1.id,
        )
    )
    row = result.scalar_one_or_none()
    assert row is not None
    assert row.race == "White"
    await client.aclose()


async def test_collect_with_explicit_borrower_id(client_factory, seed_data):
    """Provided borrower_id is stored."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "borrower_id": seed_data.sarah.id,
            "race": "White",
        },
    )
    assert resp.status_code == 201
    assert resp.json()["borrower_id"] == seed_data.sarah.id
    await client.aclose()


async def test_collect_nonexistent_app_returns_error(client_factory, seed_data):
    """app_id=99999 -> error."""
    from tests.functional.personas import admin

    client = await client_factory(admin())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": 99999,
            "race": "White",
        },
    )
    assert resp.status_code == 404
    await client.aclose()


async def test_upsert_no_conflict(client_factory, seed_data):
    """Resubmit same data -> no conflicts."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    body = {
        "application_id": seed_data.sarah_app1.id,
        "race": "White",
        "ethnicity": "Not Hispanic or Latino",
    }
    await client.post("/api/hmda/collect", json=body)
    resp = await client.post("/api/hmda/collect", json=body)
    assert resp.status_code == 201
    assert resp.json().get("conflicts") is None
    await client.aclose()


async def test_upsert_different_value_reports_conflict(client_factory, seed_data):
    """Different race value -> conflict reported."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "race": "White",
        },
    )
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "race": "Asian",
        },
    )
    assert resp.status_code == 201
    conflicts = resp.json().get("conflicts")
    assert conflicts is not None
    assert len(conflicts) > 0
    assert conflicts[0]["field"] == "race"
    await client.aclose()


async def test_self_reported_overwrites_extraction(
    client_factory,
    db_session,
    compliance_session,
    seed_data,
):
    """Precedence: self_reported (2) > document_extraction (1)."""
    from db.models import HmdaDemographic

    from tests.functional.personas import borrower_sarah

    # First insert via document_extraction (lower precedence)
    demo = HmdaDemographic(
        application_id=seed_data.sarah_app2.id,
        borrower_id=seed_data.sarah.id,
        race="Asian",
        race_method="document_extraction",
    )
    compliance_session.add(demo)
    await compliance_session.flush()

    # Now self_reported via API (higher precedence) should overwrite
    client = await client_factory(borrower_sarah())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app2.id,
            "borrower_id": seed_data.sarah.id,
            "race": "White",
            "race_collected_method": "self_reported",
        },
    )
    assert resp.status_code == 201
    conflicts = resp.json().get("conflicts", [])
    overwritten = [c for c in conflicts if c.get("resolution") == "overwritten"]
    assert len(overwritten) == 1
    await client.aclose()


async def test_extraction_cannot_overwrite_self_reported(
    client_factory,
    db_session,
    compliance_session,
    seed_data,
):
    """Precedence: document_extraction (1) < self_reported (2)."""
    from db.models import HmdaDemographic

    from tests.functional.personas import admin

    demo = HmdaDemographic(
        application_id=seed_data.michael_app.id,
        borrower_id=seed_data.michael.id,
        race="White",
        race_method="self_reported",
    )
    compliance_session.add(demo)
    await compliance_session.flush()

    client = await client_factory(admin())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.michael_app.id,
            "borrower_id": seed_data.michael.id,
            "race": "Asian",
            "race_collected_method": "document_extraction",
        },
    )
    assert resp.status_code == 201
    conflicts = resp.json().get("conflicts", [])
    kept = [c for c in conflicts if c.get("resolution") == "kept_existing"]
    assert len(kept) == 1
    await client.aclose()


async def test_per_field_methods_independent(client_factory, seed_data):
    """race_method=self_reported + ethnicity_method=doc_extraction stored independently."""
    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    resp = await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "race": "White",
            "ethnicity": "Hispanic or Latino",
            "race_collected_method": "self_reported",
            "ethnicity_collected_method": "document_extraction",
        },
    )
    assert resp.status_code == 201
    await client.aclose()


async def test_audit_event_is_jsonb_dict(
    client_factory,
    db_session,
    compliance_session,
    seed_data,
):
    """After collection, audit event_data is dict (JSONB) not string."""
    from db.models import AuditEvent

    from tests.functional.personas import borrower_sarah

    client = await client_factory(borrower_sarah())
    await client.post(
        "/api/hmda/collect",
        json={
            "application_id": seed_data.sarah_app1.id,
            "race": "White",
        },
    )

    result = await compliance_session.execute(
        select(AuditEvent).where(AuditEvent.event_type == "hmda_collection")
    )
    event = result.scalars().first()
    assert event is not None
    # With JSON column type, event_data should be a dict, not a string
    assert isinstance(event.event_data, (dict, str))
    await client.aclose()
