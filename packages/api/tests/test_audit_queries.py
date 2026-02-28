# This project was developed with assistance from AI tools.
"""Tests for CEO audit trail query and export endpoints (F13/F15)."""

import csv
import io
import json
from unittest.mock import AsyncMock, MagicMock

import pytest
from db.enums import DecisionType

from src.services.audit import (
    export_events,
    get_decision_trace,
    get_events_by_decision,
    search_events,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_audit_event(
    id=1,
    event_type="tool_call",
    user_id="system",
    user_role="system",
    application_id=None,
    decision_id=None,
    event_data=None,
    prev_hash="abc",
):
    """Build a mock AuditEvent."""
    import datetime

    evt = MagicMock()
    evt.id = id
    evt.timestamp = datetime.datetime(2026, 2, 28, 12, 0, 0, tzinfo=datetime.UTC)
    evt.event_type = event_type
    evt.user_id = user_id
    evt.user_role = user_role
    evt.application_id = application_id
    evt.decision_id = decision_id
    evt.event_data = event_data
    evt.prev_hash = prev_hash
    return evt


def _make_decision(id=1, application_id=10, decision_type=DecisionType.DENIED):
    dec = MagicMock()
    dec.id = id
    dec.application_id = application_id
    dec.decision_type = decision_type
    dec.rationale = "High DTI"
    dec.ai_recommendation = "Deny"
    dec.ai_agreement = True
    dec.override_rationale = None
    dec.denial_reasons = ["High DTI"]
    dec.decided_by = "uw-test"
    return dec


# ---------------------------------------------------------------------------
# Service: get_events_by_decision
# ---------------------------------------------------------------------------


class TestGetEventsByDecision:
    @pytest.mark.asyncio
    async def test_should_return_events_for_decision_application(self):
        """Events returned for the decision's application."""
        session = AsyncMock()
        dec = _make_decision(id=5, application_id=42)
        session.get = AsyncMock(return_value=dec)

        evts = [
            _make_audit_event(id=1, application_id=42),
            _make_audit_event(id=2, application_id=42, event_type="stage_transition"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_events_by_decision(session, 5)
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_should_return_empty_for_missing_decision(self):
        """Non-existent decision returns empty list."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        result = await get_events_by_decision(session, 999)
        assert result == []


# ---------------------------------------------------------------------------
# Service: search_events
# ---------------------------------------------------------------------------


class TestSearchEvents:
    @pytest.mark.asyncio
    async def test_should_filter_by_event_type(self):
        """Events filtered by event_type."""
        session = AsyncMock()
        evts = [_make_audit_event(id=1, event_type="decision")]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        result = await search_events(session, event_type="decision")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_should_return_empty_when_no_matches(self):
        """No matching events returns empty list."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        result = await search_events(session, days=7, event_type="nonexistent")
        assert result == []


# ---------------------------------------------------------------------------
# Service: get_decision_trace
# ---------------------------------------------------------------------------


class TestDecisionTrace:
    @pytest.mark.asyncio
    async def test_should_return_structured_trace(self):
        """Decision trace includes grouped events and decision metadata."""
        session = AsyncMock()
        dec = _make_decision(id=5, application_id=42)
        session.get = AsyncMock(return_value=dec)

        evts = [
            _make_audit_event(id=1, application_id=42, event_type="tool_call"),
            _make_audit_event(id=2, application_id=42, event_type="stage_transition"),
            _make_audit_event(id=3, application_id=42, event_type="tool_call"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        result = await get_decision_trace(session, 5)
        assert result is not None
        assert result["decision_id"] == 5
        assert result["application_id"] == 42
        assert result["decision_type"] == "denied"
        assert result["total_events"] == 3
        assert len(result["events_by_type"]["tool_call"]) == 2
        assert len(result["events_by_type"]["stage_transition"]) == 1

    @pytest.mark.asyncio
    async def test_should_return_none_for_missing_decision(self):
        """Non-existent decision returns None."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        result = await get_decision_trace(session, 999)
        assert result is None


# ---------------------------------------------------------------------------
# Service: export_events
# ---------------------------------------------------------------------------


class TestExportEvents:
    @pytest.mark.asyncio
    async def test_should_export_json(self):
        """JSON export produces valid JSON array."""
        session = AsyncMock()
        evts = [_make_audit_event(id=1), _make_audit_event(id=2)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        content, media_type = await export_events(session, fmt="json")
        assert media_type == "application/json"
        data = json.loads(content)
        assert len(data) == 2
        assert data[0]["event_id"] == 1

    @pytest.mark.asyncio
    async def test_should_export_csv(self):
        """CSV export produces valid CSV with headers."""
        session = AsyncMock()
        evts = [_make_audit_event(id=1)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        content, media_type = await export_events(session, fmt="csv")
        assert media_type == "text/csv"
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["event_id"] == "1"
        assert "prev_hash" in rows[0]

    @pytest.mark.asyncio
    async def test_should_export_empty_dataset(self):
        """Empty result set produces valid output."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        session.execute = AsyncMock(return_value=mock_result)

        content, media_type = await export_events(session, fmt="json")
        data = json.loads(content)
        assert data == []


# ---------------------------------------------------------------------------
# REST endpoint tests (functional, with mock DB)
# ---------------------------------------------------------------------------


class TestAuditEndpointsFunctional:
    """Functional tests for audit endpoints with mock DB sessions."""

    @pytest.fixture(autouse=True)
    def _clean(self):
        from src.main import app

        yield
        app.dependency_overrides.clear()

    def _make_client(self, mock_session):
        from fastapi.testclient import TestClient

        from src.main import app
        from tests.functional.mock_db import configure_app_for_persona
        from tests.functional.personas import ceo

        configure_app_for_persona(app, ceo(), mock_session)
        return TestClient(app)

    def test_should_return_audit_by_application(self):
        """GET /api/audit/application/{id} returns 200."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_audit_event(id=1, application_id=10),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        client = self._make_client(session)
        response = client.get("/api/audit/application/10")
        assert response.status_code == 200
        body = response.json()
        assert body["application_id"] == 10
        assert body["count"] == 1

    def test_should_return_audit_by_decision(self):
        """GET /api/audit/decision/{id} returns 200."""
        session = AsyncMock()
        dec = _make_decision(id=5, application_id=42)
        session.get = AsyncMock(return_value=dec)

        evts = [_make_audit_event(id=1, application_id=42)]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        client = self._make_client(session)
        response = client.get("/api/audit/decision/5")
        assert response.status_code == 200
        body = response.json()
        assert body["decision_id"] == 5
        assert body["count"] == 1

    def test_should_return_decision_trace(self):
        """GET /api/audit/decision/{id}/trace returns structured trace."""
        session = AsyncMock()
        dec = _make_decision(id=5, application_id=42)
        session.get = AsyncMock(return_value=dec)

        evts = [
            _make_audit_event(id=1, application_id=42, event_type="tool_call"),
            _make_audit_event(id=2, application_id=42, event_type="decision"),
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = evts
        session.execute = AsyncMock(return_value=mock_result)

        client = self._make_client(session)
        response = client.get("/api/audit/decision/5/trace")
        assert response.status_code == 200
        body = response.json()
        assert body["decision_id"] == 5
        assert body["total_events"] == 2
        assert "tool_call" in body["events_by_type"]

    def test_should_return_404_for_missing_decision_trace(self):
        """GET /api/audit/decision/{id}/trace returns 404 for missing decision."""
        session = AsyncMock()
        session.get = AsyncMock(return_value=None)

        client = self._make_client(session)
        response = client.get("/api/audit/decision/999/trace")
        assert response.status_code == 404

    def test_should_return_audit_search(self):
        """GET /api/audit/search returns 200 with events."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [
            _make_audit_event(id=1, event_type="decision"),
        ]
        session.execute = AsyncMock(return_value=mock_result)

        client = self._make_client(session)
        response = client.get("/api/audit/search", params={"event_type": "decision", "days": 90})
        assert response.status_code == 200
        body = response.json()
        assert body["count"] == 1

    def test_should_export_json(self):
        """GET /api/audit/export?fmt=json returns JSON attachment."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_audit_event(id=1)]
        session.execute = AsyncMock(return_value=mock_result)
        # write_audit_event needs advisory lock + flush
        session.commit = AsyncMock()

        client = self._make_client(session)
        response = client.get("/api/audit/export", params={"fmt": "json"})
        assert response.status_code == 200
        assert "application/json" in response.headers.get("content-type", "")
        assert "attachment" in response.headers.get("content-disposition", "")

    def test_should_export_csv(self):
        """GET /api/audit/export?fmt=csv returns CSV attachment."""
        session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [_make_audit_event(id=1)]
        session.execute = AsyncMock(return_value=mock_result)
        session.commit = AsyncMock()

        client = self._make_client(session)
        response = client.get("/api/audit/export", params={"fmt": "csv"})
        assert response.status_code == 200
        assert "text/csv" in response.headers.get("content-type", "")

    def test_should_reject_invalid_export_format(self):
        """GET /api/audit/export?fmt=xml returns 422."""
        session = AsyncMock()
        client = self._make_client(session)
        response = client.get("/api/audit/export", params={"fmt": "xml"})
        assert response.status_code == 422

    def test_should_deny_borrower_access(self):
        """GET /api/audit/search returns 403 for borrower role."""
        from fastapi.testclient import TestClient

        from src.core.config import settings
        from src.main import app
        from tests.functional.mock_db import configure_app_for_persona, make_mock_session
        from tests.functional.personas import borrower_sarah

        original = settings.AUTH_DISABLED
        settings.AUTH_DISABLED = False
        try:
            configure_app_for_persona(app, borrower_sarah(), make_mock_session())
            client = TestClient(app)
            response = client.get("/api/audit/search")
            assert response.status_code == 403
        finally:
            settings.AUTH_DISABLED = original
            app.dependency_overrides.clear()

    def test_should_deny_lo_export_access(self):
        """GET /api/audit/export returns 403 for loan officer role."""
        from fastapi.testclient import TestClient

        from src.core.config import settings
        from src.main import app
        from tests.functional.mock_db import configure_app_for_persona, make_mock_session
        from tests.functional.personas import loan_officer

        original = settings.AUTH_DISABLED
        settings.AUTH_DISABLED = False
        try:
            configure_app_for_persona(app, loan_officer(), make_mock_session())
            client = TestClient(app)
            response = client.get("/api/audit/export")
            assert response.status_code == 403
        finally:
            settings.AUTH_DISABLED = original
            app.dependency_overrides.clear()
