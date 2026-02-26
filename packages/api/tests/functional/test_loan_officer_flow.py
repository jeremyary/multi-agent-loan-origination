# This project was developed with assistance from AI tools.
"""Functional tests: Loan Officer persona journey.

Loan officers see only applications assigned to them. They can update
applications. Unassigned apps return 404.
"""

import pytest

from .data_factory import lo_assigned_applications, make_app_sarah_1
from .mock_db import make_mock_session
from .personas import loan_officer

pytestmark = pytest.mark.functional


class TestLoanOfficerVisibility:
    """LO sees assigned apps only (101 + 103, not 102 which is unassigned)."""

    def test_list_assigned_applications(self, make_client):
        apps = lo_assigned_applications()
        client = make_client(loan_officer(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2

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
