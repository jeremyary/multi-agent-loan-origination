# This project was developed with assistance from AI tools.
"""Functional tests: Underwriter persona journey.

Underwriters have full pipeline access -- they see all applications
with full PII and can update them.
"""

import pytest

from .data_factory import all_applications, make_app_michael
from .mock_db import make_mock_session
from .personas import underwriter

pytestmark = pytest.mark.functional


class TestUnderwriterVisibility:
    """Underwriter sees all applications with full PII."""

    def test_list_all_applications(self, make_client):
        apps = all_applications()
        client = make_client(underwriter(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 3

    def test_get_application_with_pii(self, make_client):
        app = make_app_michael()
        client = make_client(underwriter(), make_mock_session(single=app))

        resp = client.get("/api/applications/103")
        assert resp.status_code == 200
        data = resp.json()
        assert data["borrowers"][0]["ssn"] == "987-65-4321"


class TestUnderwriterCanUpdate:
    """Underwriter can update applications."""

    def test_patch_application(self, make_client):
        app = make_app_michael()
        client = make_client(underwriter(), make_mock_session(single=app))

        resp = client.patch(
            "/api/applications/103",
            json={
                "stage": "conditional_approval",
            },
        )
        assert resp.status_code == 200

    def test_underwriter_cannot_create_application(self, monkeypatch, make_client):
        """Underwriters cannot create applications (borrower/admin only)."""
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(underwriter(), make_mock_session())
        resp = client.post("/api/applications/", json={})
        assert resp.status_code == 403
