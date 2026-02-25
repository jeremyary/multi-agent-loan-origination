# This project was developed with assistance from AI tools.
"""Functional tests: Document upload across personas.

Tests the POST /applications/{id}/documents endpoint through the real app
with mocked DB and storage. Verifies:
- Borrower can upload to own application (201)
- Out-of-scope application returns 404
- Loan officer can upload to assigned application (201)
- CEO and underwriter are denied (403)
- Content-type validation rejects unsupported files (422)
"""

from io import BytesIO

import pytest

from .data_factory import make_app_sarah_1
from .mock_db import make_upload_session
from .personas import borrower_sarah, ceo, loan_officer, underwriter

pytestmark = pytest.mark.functional


def _post_upload(client, application_id=101, content_type="application/pdf", filename="test.pdf"):
    """Helper: POST a file to the upload endpoint."""
    data = b"%PDF-1.4 fake document content"
    return client.post(
        f"/api/applications/{application_id}/documents",
        files={"file": (filename, BytesIO(data), content_type)},
        data={"doc_type": "w2"},
    )


# ---------------------------------------------------------------------------
# Borrower upload
# ---------------------------------------------------------------------------


class TestBorrowerUpload:
    """Borrower upload: own app succeeds, out-of-scope app returns 404."""

    def test_upload_to_own_application(self, make_upload_client):
        app = make_app_sarah_1()
        session = make_upload_session(application=app)
        client, mock_storage = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, application_id=101)
        assert resp.status_code == 201
        data = resp.json()
        assert data["application_id"] == 101
        assert data["doc_type"] == "w2"
        assert data["status"] == "processing"
        mock_storage.upload_file.assert_called_once()

    def test_out_of_scope_application_returns_404(self, make_upload_client):
        """Data scope filters out the application -> service returns None -> 404."""
        session = make_upload_session(application=None)
        client, _ = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, application_id=999)
        assert resp.status_code == 404
        assert "Application not found" in resp.json()["detail"]


# ---------------------------------------------------------------------------
# Loan officer upload
# ---------------------------------------------------------------------------


class TestLoanOfficerUpload:
    """Loan officer can upload documents to assigned applications."""

    def test_upload_to_assigned_application(self, make_upload_client):
        app = make_app_sarah_1()
        session = make_upload_session(application=app)
        client, mock_storage = make_upload_client(loan_officer(), session)

        resp = _post_upload(client, application_id=101)
        assert resp.status_code == 201
        mock_storage.upload_file.assert_called_once()


# ---------------------------------------------------------------------------
# Upload permission matrix (denied roles)
# ---------------------------------------------------------------------------


class TestUploadPermissionMatrix:
    """Roles not in UPLOAD_ROLES are denied with 403.

    Prospect denial is in test_prospect_flow.py with the other prospect denials.
    """

    def test_ceo_denied(self, monkeypatch, make_upload_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        session = make_upload_session()
        client, _ = make_upload_client(ceo(), session)
        resp = _post_upload(client)
        assert resp.status_code == 403

    def test_underwriter_denied(self, monkeypatch, make_upload_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        session = make_upload_session()
        client, _ = make_upload_client(underwriter(), session)
        resp = _post_upload(client)
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Validation through the real app
# ---------------------------------------------------------------------------


class TestUploadValidation:
    """Content-type validation runs through the real route."""

    def test_rejects_text_file(self, make_upload_client):
        app = make_app_sarah_1()
        session = make_upload_session(application=app)
        client, _ = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, content_type="text/plain", filename="readme.txt")
        assert resp.status_code == 422
        assert "Unsupported file type" in resp.json()["detail"]

    def test_accepts_jpeg(self, make_upload_client):
        app = make_app_sarah_1()
        session = make_upload_session(application=app)
        client, _ = make_upload_client(borrower_sarah(), session)

        resp = _post_upload(client, content_type="image/jpeg", filename="id-front.jpg")
        assert resp.status_code == 201
