# This project was developed with assistance from AI tools.
"""Functional tests: Loan Officer persona journey.

Loan officers see only applications assigned to them. They can update
applications. Unassigned apps return 404. Pipeline views include urgency
metadata with sorting and filtering.
"""

from unittest.mock import AsyncMock, patch

import pytest

from src.schemas.urgency import UrgencyIndicator, UrgencyLevel

from .data_factory import lo_assigned_applications, make_app_sarah_1
from .mock_db import make_mock_session
from .personas import borrower_sarah, loan_officer

pytestmark = pytest.mark.functional

# Reusable urgency indicators for patching
_URGENCY_CRITICAL = UrgencyIndicator(
    level=UrgencyLevel.CRITICAL,
    factors=["Rate lock expires in 2 days"],
    days_in_stage=5,
    expected_stage_days=7,
)
_URGENCY_NORMAL = UrgencyIndicator(
    level=UrgencyLevel.NORMAL,
    factors=[],
    days_in_stage=1,
    expected_stage_days=5,
)


class TestLoanOfficerVisibility:
    """LO sees assigned apps only (101 + 103, not 102 which is unassigned)."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_list_assigned_applications(self, mock_urgency, make_client):
        apps = lo_assigned_applications()
        mock_urgency.return_value = {
            101: _URGENCY_CRITICAL,
            103: _URGENCY_NORMAL,
        }
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 2

    def test_get_assigned_application(self, make_client):
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 101
        # LO sees full PII
        assert data["borrowers"][0]["ssn"] == "123-45-6789"

    def test_unassigned_returns_404(self, make_client):
        """App 102 is unassigned, so LO gets 404."""
        client = make_client(loan_officer(), make_mock_session(single=None))

        resp = client.get("/api/applications/102")
        assert resp.status_code == 404


class TestLoanOfficerCanUpdate:
    """LO can PATCH assigned applications."""

    def test_patch_application(self, make_client):
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))

        resp = client.patch(
            "/api/applications/101",
            json={
                "property_address": "789 Updated Blvd",
            },
        )
        assert resp.status_code == 200

    def test_patch_unassigned_returns_404(self, make_client):
        client = make_client(loan_officer(), make_mock_session(single=None))

        resp = client.patch(
            "/api/applications/102",
            json={
                "property_address": "Should fail",
            },
        )
        assert resp.status_code == 404


class TestLoanOfficerPipeline:
    """Pipeline enhancements: urgency metadata, sorting, filtering."""

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_lo_gets_urgency_in_list_response(self, mock_urgency, make_client):
        """LO list response includes urgency indicators."""
        apps = lo_assigned_applications()
        mock_urgency.return_value = {
            101: _URGENCY_CRITICAL,
            103: _URGENCY_NORMAL,
        }
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()

        # Both items should have urgency
        for item in data["data"]:
            assert item["urgency"] is not None
            assert "level" in item["urgency"]
            assert "factors" in item["urgency"]

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_sort_by_urgency_critical_first(self, mock_urgency, make_client):
        """Sorting by urgency puts Critical apps first."""
        apps = lo_assigned_applications()
        mock_urgency.return_value = {
            101: _URGENCY_CRITICAL,
            103: _URGENCY_NORMAL,
        }
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/?sort_by=urgency")
        assert resp.status_code == 200
        data = resp.json()

        levels = [item["urgency"]["level"] for item in data["data"]]
        assert levels[0] == "critical"

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_filter_by_stage(self, mock_urgency, make_client):
        """filter_stage query param is accepted."""
        apps = lo_assigned_applications()
        mock_urgency.return_value = {
            101: _URGENCY_NORMAL,
            103: _URGENCY_NORMAL,
        }
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/?filter_stage=application")
        assert resp.status_code == 200

    @patch("src.routes.applications.compute_urgency", new_callable=AsyncMock)
    def test_filter_stalled(self, mock_urgency, make_client):
        """filter_stalled query param is accepted."""
        apps = lo_assigned_applications()
        mock_urgency.return_value = {
            101: _URGENCY_NORMAL,
            103: _URGENCY_NORMAL,
        }
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/?filter_stalled=true")
        assert resp.status_code == 200

    def test_borrower_does_not_get_urgency(self, make_client):
        """Non-LO roles get null urgency."""
        from .data_factory import sarah_applications

        apps = sarah_applications()
        client = make_client(borrower_sarah(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()

        for item in data["data"]:
            assert item["urgency"] is None
