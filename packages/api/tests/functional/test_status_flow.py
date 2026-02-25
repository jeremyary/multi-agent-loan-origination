# This project was developed with assistance from AI tools.
"""Functional tests: Application status endpoint across personas.

Validates that status responses include correct stage info, pending actions,
and respect data scope (borrowers see own, LO sees assigned, CEO sees all,
prospect blocked).
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.enums import DocumentStatus, DocumentType

from .data_factory import make_app_sarah_1
from .personas import borrower_sarah, ceo, loan_officer, prospect

pytestmark = pytest.mark.functional


def _make_status_session(application, documents, condition_count=0):
    """Build a mock session for the status endpoint.

    The status service runs:
      1. check_completeness -> app query -> unique().scalar_one_or_none()
      2. check_completeness -> doc query -> scalars().all()
      3. get_application -> app query -> unique().scalar_one_or_none()
      4. condition count -> scalar()
    """
    session = AsyncMock()

    # 1. completeness app lookup
    app_result_1 = MagicMock()
    app_result_1.unique.return_value.scalar_one_or_none.return_value = application

    # 2. completeness doc query
    doc_result = MagicMock()
    doc_result.scalars.return_value.all.return_value = documents

    # 3. get_application app lookup
    app_result_2 = MagicMock()
    app_result_2.unique.return_value.scalar_one_or_none.return_value = application

    # 4. condition count
    count_result = MagicMock()
    count_result.scalar.return_value = condition_count

    session.execute = AsyncMock(side_effect=[app_result_1, doc_result, app_result_2, count_result])
    return session


def _make_doc(doc_id, doc_type, status=DocumentStatus.UPLOADED):
    doc = MagicMock()
    doc.id = doc_id
    doc.doc_type = doc_type
    doc.status = status
    doc.quality_flags = None
    doc.created_at = MagicMock()
    doc.application = make_app_sarah_1()
    return doc


class TestBorrowerStatus:
    """Borrower sees status on own application."""

    def test_borrower_sees_status_with_pending_actions(self, app, make_client):
        sarah_app = make_app_sarah_1()
        docs = [
            _make_doc(1, DocumentType.W2),
            _make_doc(2, DocumentType.PAY_STUB),
        ]
        session = _make_status_session(sarah_app, docs)
        client = make_client(borrower_sarah(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["stage"] == "application"
        assert data["stage_info"]["label"] == "Application"
        assert data["is_document_complete"] is False
        assert data["provided_doc_count"] == 2
        assert data["required_doc_count"] == 4

        upload_actions = [
            a for a in data["pending_actions"] if a["action_type"] == "upload_document"
        ]
        assert len(upload_actions) == 2

    def test_borrower_blocked_from_other_app(self, app, make_client):
        session = _make_status_session(None, [])
        client = make_client(borrower_sarah(), session)

        resp = client.get("/api/applications/99999/status")
        assert resp.status_code == 404


class TestLoanOfficerStatus:
    def test_lo_sees_assigned_app_status(self, app, make_client):
        sarah_app = make_app_sarah_1()
        docs = [_make_doc(1, DocumentType.W2)]
        session = _make_status_session(sarah_app, docs, condition_count=2)
        client = make_client(loan_officer(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["open_condition_count"] == 2

        cond_actions = [
            a for a in data["pending_actions"] if a["action_type"] == "clear_conditions"
        ]
        assert len(cond_actions) == 1


class TestCeoStatus:
    def test_ceo_sees_status(self, app, make_client):
        sarah_app = make_app_sarah_1()
        docs = []
        session = _make_status_session(sarah_app, docs)
        client = make_client(ceo(), session)

        resp = client.get(f"/api/applications/{sarah_app.id}/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_document_complete"] is False


class TestProspectBlocked:
    def test_prospect_blocked(self, monkeypatch, app, make_client):
        from src.core.config import settings

        monkeypatch.setattr(settings, "AUTH_DISABLED", False)

        session = AsyncMock()
        client = make_client(prospect(), session)
        resp = client.get("/api/applications/101/status")
        assert resp.status_code == 403
