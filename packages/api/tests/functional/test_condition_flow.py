# This project was developed with assistance from AI tools.
"""Functional tests: Condition listing and response endpoints across personas.

Validates that condition endpoints respect data scope (borrowers see own,
LO sees assigned, prospect blocked) and return correct response shapes
through the real FastAPI app with mocked DB.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.enums import ConditionSeverity, ConditionStatus

from .data_factory import make_app_sarah_1
from .personas import borrower_sarah, loan_officer, prospect, underwriter

pytestmark = pytest.mark.functional


def _mock_condition(
    id=1,
    description="Verify employment",
    severity=ConditionSeverity.PRIOR_TO_APPROVAL,
    status=ConditionStatus.OPEN,
    response_text=None,
    issued_by="maria-uuid",
):
    c = MagicMock()
    c.id = id
    c.description = description
    c.severity = severity
    c.status = status
    c.response_text = response_text
    c.issued_by = issued_by
    c.created_at = MagicMock()
    c.created_at.isoformat.return_value = "2026-02-20T00:00:00+00:00"
    return c


def _make_conditions_session(application, conditions):
    """Build a mock session for the conditions list endpoint.

    The conditions service runs two queries:
      1. Application lookup (with data scope) -> unique().scalar_one_or_none()
      2. Condition query -> scalars().all()
    """
    session = AsyncMock()

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = application

    cond_result = MagicMock()
    cond_result.scalars.return_value.all.return_value = conditions

    session.execute = AsyncMock(side_effect=[app_result, cond_result])
    return session


def _make_respond_session(application, condition):
    """Build a mock session for the respond-to-condition endpoint.

    The respond service runs these queries:
      1. Application lookup -> unique().scalar_one_or_none()
      2. Condition lookup -> scalar_one_or_none()
      3+ Audit event writes (advisory lock, latest event query, flush)
    Then commits and refreshes.
    """
    session = AsyncMock()

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = application

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = condition

    # Audit event queries return generic mocks (advisory lock, latest event)
    audit_lock_result = MagicMock()
    audit_latest_result = MagicMock()
    audit_latest_result.scalar_one_or_none.return_value = None  # No prior events

    session.execute = AsyncMock(
        side_effect=[app_result, cond_result, audit_lock_result, audit_latest_result]
    )
    return session


class TestBorrowerListConditions:
    """Borrower can list conditions on own application."""

    def test_borrower_sees_conditions(self, app, make_client):
        sarah_app = make_app_sarah_1()
        conditions = [
            _mock_condition(id=1, description="Verify employment", status=ConditionStatus.OPEN),
            _mock_condition(
                id=2,
                description="Bank statements",
                status=ConditionStatus.RESPONDED,
                response_text="Uploaded both months",
            ),
        ]
        session = _make_conditions_session(sarah_app, conditions)
        client = make_client(borrower_sarah(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/conditions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert data["data"][0]["description"] == "Verify employment"
        assert data["data"][0]["status"] == "open"
        assert data["data"][1]["response_text"] == "Uploaded both months"

    def test_borrower_sees_empty_conditions(self, app, make_client):
        sarah_app = make_app_sarah_1()
        session = _make_conditions_session(sarah_app, [])
        client = make_client(borrower_sarah(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/conditions")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 0
        assert data["data"] == []

    def test_borrower_cannot_see_other_app(self, app, make_client):
        session = _make_conditions_session(None, [])
        client = make_client(borrower_sarah(), session)

        resp = client.get("/api/applications/99999/conditions")
        assert resp.status_code == 404


class TestBorrowerRespondToCondition:
    """Borrower can respond to conditions with text."""

    def test_borrower_responds_to_condition(self, app, make_client):
        sarah_app = make_app_sarah_1()
        condition = _mock_condition(
            id=5,
            description="Explain large deposit",
            status=ConditionStatus.OPEN,
        )
        session = _make_respond_session(sarah_app, condition)
        client = make_client(borrower_sarah(), session)

        resp = client.post(
            f"/api/applications/{sarah_app.id}/conditions/5/respond",
            json={"response_text": "Gift from my parents for down payment"},
        )
        assert resp.status_code == 200
        data = resp.json()["data"]
        assert data["id"] == 5

    def test_respond_to_missing_condition(self, app, make_client):
        sarah_app = make_app_sarah_1()
        session = _make_respond_session(sarah_app, None)
        client = make_client(borrower_sarah(), session)

        resp = client.post(
            f"/api/applications/{sarah_app.id}/conditions/999/respond",
            json={"response_text": "my response"},
        )
        assert resp.status_code == 404


class TestLoanOfficerConditions:
    """LO can list conditions on assigned applications."""

    def test_lo_sees_conditions(self, app, make_client):
        sarah_app = make_app_sarah_1()
        conditions = [
            _mock_condition(id=1, description="Verify employment"),
        ]
        session = _make_conditions_session(sarah_app, conditions)
        client = make_client(loan_officer(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/conditions")
        assert resp.status_code == 200
        assert resp.json()["count"] == 1


class TestUnderwriterConditions:
    """Underwriter can list conditions."""

    def test_underwriter_sees_conditions(self, app, make_client):
        sarah_app = make_app_sarah_1()
        conditions = [_mock_condition(id=1)]
        session = _make_conditions_session(sarah_app, conditions)
        client = make_client(underwriter(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/conditions")
        assert resp.status_code == 200


class TestProspectBlocked:
    """Prospect cannot access conditions endpoint."""

    def test_prospect_blocked(self, monkeypatch, app, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        session = AsyncMock()
        client = make_client(prospect(), session)
        resp = client.get("/api/applications/101/conditions")
        assert resp.status_code == 403
