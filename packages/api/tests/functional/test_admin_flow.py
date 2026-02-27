# This project was developed with assistance from AI tools.
"""Functional tests: Admin persona journey.

Admin has full pipeline access with no PII masking. Can access admin-only
endpoints like seed status and audit queries.
"""

import pytest

from .data_factory import all_applications, make_app_sarah_1
from .mock_db import make_mock_session
from .personas import admin, borrower_sarah

pytestmark = pytest.mark.functional


class TestAdminFullAccess:
    """Admin sees all applications with full PII."""

    def test_list_all_applications(self, make_client):
        apps = all_applications()
        client = make_client(admin(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 3

    def test_get_application_with_unmasked_pii(self, make_client):
        app = make_app_sarah_1()
        client = make_client(admin(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["borrowers"][0]["ssn"] == "123-45-6789"

    def test_patch_application(self, make_client):
        app = make_app_sarah_1()
        client = make_client(admin(), make_mock_session(single=app))

        resp = client.patch(
            "/api/applications/101",
            json={
                "property_address": "Admin Override",
            },
        )
        assert resp.status_code == 200


class TestAdminOnlyEndpoints:
    """Admin-only endpoints reject non-admin roles."""

    def test_seed_status_accessible(self, make_client):
        from unittest.mock import MagicMock

        mock_session = make_mock_session()
        # seed status queries for a SeedLog entry
        result = MagicMock()
        result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = result

        client = make_client(admin(), mock_session)
        resp = client.get("/api/admin/seed/status")
        assert resp.status_code == 200

    def test_borrower_denied_on_admin_endpoints(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(borrower_sarah(), make_mock_session())
        resp = client.get("/api/admin/seed/status")
        assert resp.status_code == 403
