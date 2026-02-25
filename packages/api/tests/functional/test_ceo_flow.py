# This project was developed with assistance from AI tools.
"""Functional tests: CEO persona journey.

CEO has full pipeline access but PII is masked: SSN -> ``***-**-NNNN``,
DOB -> ``YYYY-**-**``. Documents show metadata only; content is denied.
"""

import pytest

from .data_factory import all_applications, app_101_documents, make_app_sarah_1, make_document
from .mock_db import make_mock_session
from .personas import ceo

pytestmark = pytest.mark.functional


class TestCeoPiiMasking:
    """CEO sees masked PII in application responses."""

    def test_list_applications_with_masked_pii(self, make_client):
        apps = all_applications()
        client = make_client(ceo(), make_mock_session(items=apps))

        resp = client.get("/api/applications/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] == 3

        for item in data["data"]:
            for borrower in item.get("borrowers", []):
                if borrower.get("ssn_encrypted"):
                    assert borrower["ssn_encrypted"].startswith("***-**-")
                if borrower.get("dob"):
                    assert "**" in borrower["dob"]

    def test_get_application_ssn_masked(self, make_client):
        app = make_app_sarah_1()
        client = make_client(ceo(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        assert resp.status_code == 200
        data = resp.json()
        assert data["borrowers"][0]["ssn_encrypted"] == "***-**-6789"

    def test_get_application_dob_masked(self, make_client):
        app = make_app_sarah_1()
        client = make_client(ceo(), make_mock_session(single=app))

        resp = client.get("/api/applications/101")
        data = resp.json()
        assert data["borrowers"][0]["dob"].startswith("1990-**")


class TestCeoDocumentRestriction:
    """CEO sees document metadata only; content access is denied."""

    def test_get_document_excludes_file_path(self, make_client):
        doc = make_document()
        client = make_client(ceo(), make_mock_session(single=doc))

        resp = client.get("/api/documents/1")
        assert resp.status_code == 200
        assert "file_path" not in resp.json()

    def test_list_documents_metadata_only(self, make_client):
        docs = app_101_documents()
        client = make_client(ceo(), make_mock_session(items=docs))

        resp = client.get("/api/applications/101/documents")
        assert resp.status_code == 200
        for item in resp.json()["data"]:
            assert "file_path" not in item

    def test_document_content_denied(self, monkeypatch, make_client):
        """CEO is blocked from /documents/{id}/content at RBAC level."""
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        doc = make_document()
        client = make_client(ceo(), make_mock_session(single=doc))

        resp = client.get("/api/documents/1/content")
        assert resp.status_code == 403


class TestCeoCannotModify:
    """CEO cannot create or update applications."""

    def test_cannot_patch(self, monkeypatch, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        client = make_client(ceo(), make_mock_session())
        resp = client.patch("/api/applications/101", json={"stage": "closed"})
        assert resp.status_code == 403
