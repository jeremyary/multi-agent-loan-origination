# This project was developed with assistance from AI tools.
"""Condition listing and response with real PostgreSQL."""

import pytest

pytestmark = pytest.mark.integration


async def _add_conditions(db_session, app_id, issued_by="maria-uw"):
    """Insert test conditions and return their IDs."""
    from db.enums import ConditionSeverity, ConditionStatus
    from db.models import Condition

    c1 = Condition(
        application_id=app_id,
        description="Explain the large deposit on your bank statement",
        severity=ConditionSeverity.PRIOR_TO_APPROVAL,
        status=ConditionStatus.OPEN,
        issued_by=issued_by,
    )
    c2 = Condition(
        application_id=app_id,
        description="Provide signed employment verification letter",
        severity=ConditionSeverity.PRIOR_TO_APPROVAL,
        status=ConditionStatus.OPEN,
        issued_by=issued_by,
    )
    c3 = Condition(
        application_id=app_id,
        description="Title insurance commitment",
        severity=ConditionSeverity.PRIOR_TO_CLOSING,
        status=ConditionStatus.CLEARED,
        issued_by=issued_by,
        cleared_by=issued_by,
    )
    db_session.add_all([c1, c2, c3])
    await db_session.flush()
    return c1.id, c2.id, c3.id


class TestListConditions:
    """GET /applications/{id}/conditions."""

    async def test_borrower_sees_all_conditions(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        c1_id, c2_id, c3_id = await _add_conditions(db_session, seed_data.sarah_app1.id)

        client = await client_factory(borrower_sarah())
        resp = await client.get(f"/api/applications/{seed_data.sarah_app1.id}/conditions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3
        statuses = {c["status"] for c in data["data"]}
        assert "open" in statuses
        assert "cleared" in statuses
        await client.aclose()

    async def test_open_only_filter(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        await _add_conditions(db_session, seed_data.sarah_app1.id)

        client = await client_factory(borrower_sarah())
        resp = await client.get(
            f"/api/applications/{seed_data.sarah_app1.id}/conditions?open_only=true"
        )
        assert resp.status_code == 200
        data = resp.json()
        # Only OPEN and RESPONDED statuses, not CLEARED
        assert data["count"] == 2
        statuses = {c["status"] for c in data["data"]}
        assert "cleared" not in statuses
        await client.aclose()

    async def test_borrower_blocked_from_other_app(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        await _add_conditions(db_session, seed_data.michael_app.id)

        client = await client_factory(borrower_sarah())
        resp = await client.get(f"/api/applications/{seed_data.michael_app.id}/conditions")
        assert resp.status_code == 404
        await client.aclose()

    async def test_lo_sees_assigned_app_conditions(self, client_factory, seed_data, db_session):
        from tests.functional.personas import loan_officer

        await _add_conditions(db_session, seed_data.sarah_app1.id)

        client = await client_factory(loan_officer())
        resp = await client.get(f"/api/applications/{seed_data.sarah_app1.id}/conditions")
        assert resp.status_code == 200
        assert resp.json()["count"] == 3
        await client.aclose()


class TestRespondToCondition:
    """POST /applications/{id}/conditions/{cid}/respond."""

    async def test_borrower_responds_to_open_condition(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        c1_id, _, _ = await _add_conditions(db_session, seed_data.sarah_app1.id)

        client = await client_factory(borrower_sarah())
        resp = await client.post(
            f"/api/applications/{seed_data.sarah_app1.id}/conditions/{c1_id}/respond",
            json={"response_text": "Gift from my parents for the down payment"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == c1_id
        assert data["status"] == "responded"
        assert data["response_text"] == "Gift from my parents for the down payment"
        await client.aclose()

    async def test_respond_updates_status_to_responded(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        c1_id, _, _ = await _add_conditions(db_session, seed_data.sarah_app1.id)

        client = await client_factory(borrower_sarah())
        # Respond to condition
        await client.post(
            f"/api/applications/{seed_data.sarah_app1.id}/conditions/{c1_id}/respond",
            json={"response_text": "Gift from parents"},
        )

        # Verify via list endpoint - filter open_only to see it changed from open
        resp = await client.get(
            f"/api/applications/{seed_data.sarah_app1.id}/conditions?open_only=true"
        )
        data = resp.json()
        responded = [c for c in data["data"] if c["id"] == c1_id]
        assert len(responded) == 1
        assert responded[0]["status"] == "responded"
        assert responded[0]["response_text"] == "Gift from parents"
        await client.aclose()

    async def test_respond_to_nonexistent_condition(self, client_factory, seed_data, db_session):
        from tests.functional.personas import borrower_sarah

        client = await client_factory(borrower_sarah())
        resp = await client.post(
            f"/api/applications/{seed_data.sarah_app1.id}/conditions/99999/respond",
            json={"response_text": "my response"},
        )
        assert resp.status_code == 404
        await client.aclose()

    async def test_borrower_blocked_from_other_app_respond(
        self, client_factory, seed_data, db_session
    ):
        from tests.functional.personas import borrower_sarah

        c1_id, _, _ = await _add_conditions(db_session, seed_data.michael_app.id)

        client = await client_factory(borrower_sarah())
        resp = await client.post(
            f"/api/applications/{seed_data.michael_app.id}/conditions/{c1_id}/respond",
            json={"response_text": "my response"},
        )
        assert resp.status_code == 404
        await client.aclose()


class TestDocumentConditionLink:
    """Document linking to conditions via the condition_id FK."""

    async def test_document_has_condition_id_column(self, db_session, seed_data):
        """Verify the condition_id column exists and can be set."""
        from db.models import Document
        from sqlalchemy import select

        # seed_data.doc1 has no condition
        result = await db_session.execute(select(Document).where(Document.id == seed_data.doc1.id))
        doc = result.scalar_one()
        assert doc.condition_id is None

        # Link to a condition
        c1_id, _, _ = await _add_conditions(db_session, seed_data.sarah_app1.id)
        doc.condition_id = c1_id
        await db_session.flush()

        result2 = await db_session.execute(select(Document).where(Document.id == seed_data.doc1.id))
        updated = result2.scalar_one()
        assert updated.condition_id == c1_id
