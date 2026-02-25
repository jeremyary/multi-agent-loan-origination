# This project was developed with assistance from AI tools.
"""Functional tests: Cross-persona isolation.

The highest-value regression guard. Same mock data portfolio, different
personas, different visibility. Catches data-scope leaks that single-persona
tests miss.
"""

import pytest

from .data_factory import (
    all_applications,
    lo_assigned_applications,
    make_app_sarah_1,
    make_document,
    michael_applications,
    sarah_applications,
)
from .mock_db import make_mock_session
from .personas import (
    admin,
    borrower_michael,
    borrower_sarah,
    ceo,
    loan_officer,
    underwriter,
)

pytestmark = pytest.mark.functional


# ---------------------------------------------------------------------------
# Visibility counts: same portfolio, different counts by role
# ---------------------------------------------------------------------------


class TestVisibilityCounts:
    """Each persona sees the correct number of applications."""

    def test_borrower_sarah_sees_2(self, make_client):
        client = make_client(borrower_sarah(), make_mock_session(items=sarah_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 2

    def test_borrower_michael_sees_1(self, make_client):
        client = make_client(borrower_michael(), make_mock_session(items=michael_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 1

    def test_loan_officer_sees_2_assigned(self, make_client):
        client = make_client(loan_officer(), make_mock_session(items=lo_assigned_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 2

    def test_underwriter_sees_all_3(self, make_client):
        client = make_client(underwriter(), make_mock_session(items=all_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 3

    def test_ceo_sees_all_3(self, make_client):
        client = make_client(ceo(), make_mock_session(items=all_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 3

    def test_admin_sees_all_3(self, make_client):
        client = make_client(admin(), make_mock_session(items=all_applications()))
        resp = client.get("/api/applications/")
        assert resp.json()["count"] == 3


# ---------------------------------------------------------------------------
# PII masking: same application, different PII visibility
# ---------------------------------------------------------------------------


class TestPiiByRole:
    """Same application 101, PII visible vs masked by role."""

    def test_borrower_sees_full_ssn(self, make_client):
        app = make_app_sarah_1()
        client = make_client(borrower_sarah(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn_encrypted"] == "123-45-6789"

    def test_loan_officer_sees_full_ssn(self, make_client):
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn_encrypted"] == "123-45-6789"

    def test_underwriter_sees_full_ssn(self, make_client):
        app = make_app_sarah_1()
        client = make_client(underwriter(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn_encrypted"] == "123-45-6789"

    def test_admin_sees_full_ssn(self, make_client):
        app = make_app_sarah_1()
        client = make_client(admin(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn_encrypted"] == "123-45-6789"

    def test_ceo_sees_masked_ssn(self, make_client):
        app = make_app_sarah_1()
        client = make_client(ceo(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["ssn_encrypted"] == "***-**-6789"

    def test_ceo_sees_masked_dob(self, make_client):
        app = make_app_sarah_1()
        client = make_client(ceo(), make_mock_session(single=app))
        data = client.get("/api/applications/101").json()
        assert data["borrowers"][0]["dob"].startswith("1990-**")


# ---------------------------------------------------------------------------
# Document content: file_path visibility by role
# ---------------------------------------------------------------------------


class TestDocumentContentByRole:
    """Same document, different detail levels by role."""

    def test_loan_officer_sees_file_path(self, make_client):
        doc = make_document(file_path="/uploads/w2.pdf")
        client = make_client(loan_officer(), make_mock_session(single=doc))
        data = client.get("/api/documents/1").json()
        assert data["file_path"] == "/uploads/w2.pdf"

    def test_underwriter_sees_file_path(self, make_client):
        doc = make_document(file_path="/uploads/w2.pdf")
        client = make_client(underwriter(), make_mock_session(single=doc))
        data = client.get("/api/documents/1").json()
        assert data["file_path"] == "/uploads/w2.pdf"

    def test_ceo_does_not_see_file_path(self, make_client):
        doc = make_document(file_path="/uploads/w2.pdf")
        client = make_client(ceo(), make_mock_session(single=doc))
        data = client.get("/api/documents/1").json()
        assert "file_path" not in data


# ---------------------------------------------------------------------------
# Update permission matrix
# ---------------------------------------------------------------------------


class TestUpdatePermissionMatrix:
    """PATCH /api/applications/101 -- who can and who cannot."""

    def test_loan_officer_can_update(self, make_client):
        app = make_app_sarah_1()
        client = make_client(loan_officer(), make_mock_session(single=app))
        resp = client.patch("/api/applications/101", json={"property_address": "new"})
        assert resp.status_code == 200

    def test_underwriter_can_update(self, make_client):
        app = make_app_sarah_1()
        client = make_client(underwriter(), make_mock_session(single=app))
        resp = client.patch("/api/applications/101", json={"property_address": "new"})
        assert resp.status_code == 200

    def test_admin_can_update(self, make_client):
        app = make_app_sarah_1()
        client = make_client(admin(), make_mock_session(single=app))
        resp = client.patch("/api/applications/101", json={"property_address": "new"})
        assert resp.status_code == 200

    def test_borrower_cannot_update(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(borrower_sarah(), make_mock_session())
        resp = client.patch("/api/applications/101", json={"property_address": "new"})
        assert resp.status_code == 403

    def test_ceo_cannot_update(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(ceo(), make_mock_session())
        resp = client.patch("/api/applications/101", json={"property_address": "new"})
        assert resp.status_code == 403
