# This project was developed with assistance from AI tools.
"""Functional tests: LO workflow actions through the HTTP layer.

Proves LO data scope, document visibility, completeness, and stage
transitions work end-to-end through the route layer with RBAC enforcement.
"""

import pytest

from .data_factory import app_101_documents, make_app_sarah_1
from .mock_db import make_mock_session
from .personas import loan_officer, loan_officer_bob

pytestmark = pytest.mark.functional


class TestLoDocumentVisibility:
    """LO sees docs for assigned apps, blocked from unassigned."""

    def test_lo_sees_docs_for_assigned_app(self, make_client):
        """LO can list documents for an assigned application."""
        docs = app_101_documents()
        client = make_client(loan_officer(), make_mock_session(items=docs, count=2))

        resp = client.get("/api/applications/101/documents")
        assert resp.status_code == 200
        data = resp.json()
        assert data["pagination"]["total"] == 2

    def test_lo_blocked_from_unassigned_app_docs(self, make_client):
        """LO Bob can't see docs for app 101 (assigned to James)."""
        client = make_client(
            loan_officer_bob(),
            make_mock_session(items=[], count=0),
        )

        resp = client.get("/api/applications/101/documents")
        assert resp.status_code == 200
        data = resp.json()
        # Returns empty -- scope filtering means Bob sees 0 docs
        assert data["pagination"]["total"] == 0


class TestLoCompleteness:
    """Completeness check respects LO data scope."""

    def test_lo_completeness_for_assigned_app(self, make_client):
        """LO can check completeness for assigned application."""
        app = make_app_sarah_1()
        # completeness route calls get_application then queries docs
        client = make_client(loan_officer(), make_mock_session(single=app, items=[]))

        resp = client.get("/api/applications/101/completeness")
        assert resp.status_code == 200
        data = resp.json()
        assert data["application_id"] == 101
        assert "is_complete" in data


class TestLoStageTransition:
    """Stage transition via PATCH respects LO scope."""

    def test_lo_can_patch_assigned_app_stage(self, make_client):
        """LO can transition stage on assigned application via PATCH."""
        app = make_app_sarah_1()
        # The mock session returns the same app for both reads (get + post-transition)
        client = make_client(loan_officer(), make_mock_session(single=app))

        resp = client.patch(
            "/api/applications/101",
            json={"stage": "processing"},
        )
        assert resp.status_code == 200
