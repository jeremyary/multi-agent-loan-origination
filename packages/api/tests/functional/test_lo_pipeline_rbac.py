# This project was developed with assistance from AI tools.
"""Functional tests: Loan Officer pipeline RBAC isolation.

Proves that each LO sees only their assigned applications and cannot
access apps assigned to other LOs. Also verifies that admin, underwriter,
and CEO roles see the full pipeline.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.urgency import UrgencyIndicator, UrgencyLevel

from .data_factory import (
    all_applications,
    lo_assigned_applications,
    lo_bob_applications,
    make_app_bob_assigned,
    make_app_sarah_1,
)
from .mock_db import make_mock_session
from .personas import (
    admin,
    ceo,
    loan_officer,
    loan_officer_bob,
    underwriter,
)

pytestmark = pytest.mark.functional

_URGENCY_NORMAL = UrgencyIndicator(
    level=UrgencyLevel.NORMAL,
    factors=[],
    days_in_stage=1,
    expected_stage_days=5,
)


def _urgency_for_ids(ids: list[int]) -> dict[int, UrgencyIndicator]:
    """Build a mock urgency map returning NORMAL for given IDs."""
    return {app_id: _URGENCY_NORMAL for app_id in ids}


# ---------------------------------------------------------------------------
# Cross-LO isolation: Alice (James) vs Bob
# ---------------------------------------------------------------------------


class TestCrossLOIsolation:
    """Each LO sees only their own assigned applications."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_james_sees_only_his_apps(self, mock_urgency, make_client):
        """LO James sees apps 101 + 103 (his assignments)."""
        apps = lo_assigned_applications()
        mock_urgency.return_value = _urgency_for_ids([101, 103])
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 2
        ids = {item["id"] for item in data["data"]}
        assert ids == {101, 103}

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_bob_sees_only_his_apps(self, mock_urgency, make_client):
        """LO Bob sees only app 104 (his assignment)."""
        apps = lo_bob_applications()
        mock_urgency.return_value = _urgency_for_ids([104])
        client = make_client(loan_officer_bob(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 1
        assert data["data"][0]["id"] == 104

    def test_james_cannot_access_bobs_app(self, make_client):
        """LO James gets 404 when trying to access Bob's app 104."""
        client = make_client(loan_officer(), make_mock_session(single=None))

        resp = client.get("/api/applications/104")
        assert resp.status_code == 404

    def test_bob_cannot_access_james_app(self, make_client):
        """LO Bob gets 404 when trying to access James's app 101."""
        client = make_client(loan_officer_bob(), make_mock_session(single=None))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 404

    def test_james_cannot_update_bobs_app(self, make_client):
        """LO James gets 404 when trying to PATCH Bob's app."""
        client = make_client(loan_officer(), make_mock_session(single=None))

        resp = client.patch("/api/applications/104", json={"property_address": "hijack"})
        assert resp.status_code == 404

    def test_bob_cannot_update_james_app(self, make_client):
        """LO Bob gets 404 when trying to PATCH James's app."""
        client = make_client(loan_officer_bob(), make_mock_session(single=None))

        resp = client.patch("/api/applications/101", json={"property_address": "hijack"})
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Pipeline count matches assignments
# ---------------------------------------------------------------------------


class TestPipelineCountMatchesAssignments:
    """Pipeline total reflects only assigned applications."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_james_pipeline_count(self, mock_urgency, make_client):
        apps = lo_assigned_applications()
        mock_urgency.return_value = _urgency_for_ids([101, 103])
        client = make_client(loan_officer(), make_mock_session(items=apps))

        data = client.get("/api/applications/").json()
        assert data["pagination"]["total"] == 2

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_bob_pipeline_count(self, mock_urgency, make_client):
        apps = lo_bob_applications()
        mock_urgency.return_value = _urgency_for_ids([104])
        client = make_client(loan_officer_bob(), make_mock_session(items=apps))

        data = client.get("/api/applications/").json()
        assert data["pagination"]["total"] == 1


# ---------------------------------------------------------------------------
# Full pipeline visibility for non-LO roles
# ---------------------------------------------------------------------------


class TestFullPipelineVisibility:
    """Admin, underwriter, and CEO see the full pipeline."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_admin_sees_all(self, mock_urgency, make_client):
        apps = all_applications()
        mock_urgency.return_value = _urgency_for_ids([101, 102, 103])
        client = make_client(admin(), make_mock_session(items=apps))

        data = client.get("/api/applications/").json()
        assert data["pagination"]["total"] == 3

    def test_underwriter_sees_all(self, make_client):
        apps = all_applications()
        client = make_client(underwriter(), make_mock_session(items=apps))

        data = client.get("/api/applications/").json()
        assert data["pagination"]["total"] == 3

    def test_ceo_sees_all(self, make_client):
        apps = all_applications()
        client = make_client(ceo(), make_mock_session(items=apps))

        data = client.get("/api/applications/").json()
        assert data["pagination"]["total"] == 3

    def test_admin_can_access_any_app(self, make_client):
        app = make_app_sarah_1()
        client = make_client(admin(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200

    def test_admin_can_access_bob_app(self, make_client):
        app = make_app_bob_assigned()
        client = make_client(admin(), make_mock_session(single=app))

        resp = client.get("/api/applications/104")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# LO detail view has urgency
# ---------------------------------------------------------------------------


class TestLODetailView:
    """LO detail endpoints return expected data for assigned apps."""

    def test_lo_gets_full_detail(self, make_client):
        """LO sees full application detail for assigned app."""
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 101
        assert data["stage"] == "application"
        assert data["loan_amount"] == "350000.00"
        assert data["assigned_to"] is not None
        assert len(data["borrowers"]) == 1
        assert data["borrowers"][0]["first_name"] == "Sarah"

    def test_lo_sees_borrower_pii(self, make_client):
        """LO sees full PII (SSN, DOB) for assigned apps."""
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))

        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn"] == "123-45-6789"
        assert data["borrowers"][0]["dob"] is not None


# ---------------------------------------------------------------------------
# Status endpoint urgency enrichment
# ---------------------------------------------------------------------------


class TestStatusEndpointUrgency:
    """GET /applications/{id}/status includes urgency for LO/admin."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_lo_status_includes_urgency(self, mock_urgency, make_client):
        """LO sees urgency in status response."""
        from unittest.mock import MagicMock as MM

        app = make_app_sarah_1()

        mock_urgency.return_value = {101: _URGENCY_NORMAL}

        # Status service needs: completeness app, docs, get_app, conditions, then urgency get_app
        session = AsyncMock()

        # 1. completeness: app lookup
        r1 = MM()
        r1.unique.return_value.scalar_one_or_none.return_value = app
        # 2. completeness: docs
        r2 = MM()
        r2.scalars.return_value.all.return_value = []
        # 3. get_application
        r3 = MM()
        r3.unique.return_value.scalar_one_or_none.return_value = app
        # 4. condition count
        r4 = MM()
        r4.scalar.return_value = 0
        # 5. urgency get_application
        r5 = MM()
        r5.unique.return_value.scalar_one_or_none.return_value = app

        session.execute = AsyncMock(side_effect=[r1, r2, r3, r4, r5])

        client = make_client(loan_officer(), session)
        resp = client.get("/api/applications/101/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["urgency"] is not None
        assert data["urgency"]["level"] == "normal"

    def test_borrower_status_omits_urgency(self, make_client):
        """Borrower status response has null urgency."""
        from unittest.mock import MagicMock as MM

        from .personas import borrower_sarah

        app = make_app_sarah_1()
        session = AsyncMock()

        r1 = MM()
        r1.unique.return_value.scalar_one_or_none.return_value = app
        r2 = MM()
        r2.scalars.return_value.all.return_value = []
        r3 = MM()
        r3.unique.return_value.scalar_one_or_none.return_value = app
        r4 = MM()
        r4.scalar.return_value = 0

        session.execute = AsyncMock(side_effect=[r1, r2, r3, r4])

        client = make_client(borrower_sarah(), session)
        resp = client.get("/api/applications/101/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["urgency"] is None
