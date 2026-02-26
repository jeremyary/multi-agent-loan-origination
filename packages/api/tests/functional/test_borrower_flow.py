# This project was developed with assistance from AI tools.
"""Functional tests: Borrower persona journey.

Borrowers see only their own data. PII is visible to them (it's their data).
They cannot PATCH applications. Out-of-scope resources return 404 (not 403)
to avoid leaking existence.
"""

import pytest

from .data_factory import make_app_sarah_1, michael_applications, sarah_applications
from .mock_db import make_mock_session
from .personas import borrower_michael, borrower_sarah

pytestmark = pytest.mark.functional


class TestBorrowerSarahVisibility:
    """Sarah sees her 2 applications with full PII."""

    def test_list_own_applications(self, make_client):
        apps = sarah_applications()
        client = make_client(borrower_sarah(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 2
        assert len(data["data"]) == 2

    def test_get_own_application_with_pii(self, make_client):
        app = make_app_sarah_1()
        client = make_client(borrower_sarah(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == 101
        # PII is visible to borrower (it's their own data)
        assert data["borrowers"][0]["ssn"] == "123-45-6789"

    def test_out_of_scope_returns_404(self, make_client):
        """Sarah cannot see Michael's app -- returns 404 not 403."""
        client = make_client(borrower_sarah(), make_mock_session(single=None))

        resp = client.get("/api/applications/103")
        assert resp.status_code == 404


class TestBorrowerMichaelVisibility:
    """Michael sees only his 1 application."""

    def test_list_own_applications(self, make_client):
        apps = michael_applications()
        client = make_client(borrower_michael(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 1


class TestBorrowerCannotUpdate:
    """Borrowers cannot PATCH applications."""

    def test_patch_denied(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(borrower_sarah(), make_mock_session())
        resp = client.patch("/api/applications/101", json={"property_address": "New St"})
        assert resp.status_code == 403

    def test_borrower_cannot_access_admin(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(borrower_sarah(), make_mock_session())
        resp = client.get("/api/admin/seed/status")
        assert resp.status_code == 403
