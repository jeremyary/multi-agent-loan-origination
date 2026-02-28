# This project was developed with assistance from AI tools.
"""Audit query integration tests with real PostgreSQL.

Validates that audit trail queries (by application, decision, time range,
backward trace) and export produce correct results against a real database.
"""

import csv
import io
import json

import pytest
from db.enums import ApplicationStage, DecisionType, LoanType
from db.models import Application, AuditEvent, Decision

from src.services.audit import (
    export_events,
    get_decision_trace,
    get_events_by_application,
    get_events_by_decision,
    search_events,
)

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_audit_data(db_session):
    """Create applications, decisions, and audit events for testing."""
    import datetime

    app1 = Application(
        stage=ApplicationStage.CLOSED,
        loan_type=LoanType.CONVENTIONAL_30,
        property_address="100 Audit Ln",
        loan_amount=300000,
        property_value=400000,
    )
    app2 = Application(
        stage=ApplicationStage.DENIED,
        loan_type=LoanType.FHA,
        property_address="200 Denied Ave",
        loan_amount=200000,
        property_value=250000,
    )
    db_session.add_all([app1, app2])
    await db_session.flush()

    dec_approved = Decision(
        application_id=app1.id,
        decision_type=DecisionType.APPROVED,
        rationale="Strong financials",
        ai_recommendation="Approve",
        ai_agreement=True,
        decided_by="uw-test",
    )
    dec_denied = Decision(
        application_id=app2.id,
        decision_type=DecisionType.DENIED,
        rationale="High DTI",
        ai_recommendation="Deny",
        ai_agreement=True,
        decided_by="uw-test",
        denial_reasons=["High DTI", "Insufficient reserves"],
    )
    db_session.add_all([dec_approved, dec_denied])
    await db_session.flush()

    base = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=10)
    events = [
        AuditEvent(
            event_type="stage_transition",
            user_id="system",
            user_role="system",
            application_id=app1.id,
            event_data={"from_stage": "inquiry", "to_stage": "application"},
            timestamp=base,
        ),
        AuditEvent(
            event_type="tool_call",
            user_id="uw-test",
            user_role="underwriter",
            application_id=app1.id,
            event_data={"tool": "risk_assessment", "result": "low_risk"},
            timestamp=base + datetime.timedelta(days=1),
        ),
        AuditEvent(
            event_type="decision",
            user_id="uw-test",
            user_role="underwriter",
            application_id=app1.id,
            decision_id=dec_approved.id,
            event_data={"decision_type": "approved"},
            timestamp=base + datetime.timedelta(days=2),
        ),
        AuditEvent(
            event_type="stage_transition",
            user_id="system",
            user_role="system",
            application_id=app2.id,
            event_data={"from_stage": "inquiry", "to_stage": "application"},
            timestamp=base + datetime.timedelta(days=3),
        ),
        AuditEvent(
            event_type="decision",
            user_id="uw-test",
            user_role="underwriter",
            application_id=app2.id,
            decision_id=dec_denied.id,
            event_data={"decision_type": "denied"},
            timestamp=base + datetime.timedelta(days=5),
        ),
    ]
    db_session.add_all(events)
    await db_session.flush()

    return {
        "app1_id": app1.id,
        "app2_id": app2.id,
        "dec_approved_id": dec_approved.id,
        "dec_denied_id": dec_denied.id,
    }


# ---------------------------------------------------------------------------
# Query by application
# ---------------------------------------------------------------------------


class TestAuditByApplication:
    async def test_should_return_events_for_application(self, db_session):
        ids = await _seed_audit_data(db_session)
        events = await get_events_by_application(db_session, ids["app1_id"])
        assert len(events) == 3
        types = [e.event_type for e in events]
        assert "stage_transition" in types
        assert "tool_call" in types
        assert "decision" in types

    async def test_should_return_empty_for_unknown_application(self, db_session):
        events = await get_events_by_application(db_session, 999999)
        assert events == []


# ---------------------------------------------------------------------------
# Query by decision
# ---------------------------------------------------------------------------


class TestAuditByDecision:
    async def test_should_return_application_events_for_decision(self, db_session):
        ids = await _seed_audit_data(db_session)
        events = await get_events_by_decision(db_session, ids["dec_approved_id"])
        # All 3 events for app1
        assert len(events) == 3

    async def test_should_return_empty_for_unknown_decision(self, db_session):
        await _seed_audit_data(db_session)
        events = await get_events_by_decision(db_session, 999999)
        assert events == []


# ---------------------------------------------------------------------------
# Search by time range / event type
# ---------------------------------------------------------------------------


class TestAuditSearch:
    async def test_should_filter_by_event_type(self, db_session):
        await _seed_audit_data(db_session)
        events = await search_events(db_session, event_type="decision")
        assert all(e.event_type == "decision" for e in events)
        assert len(events) == 2

    async def test_should_filter_by_time_range(self, db_session):
        await _seed_audit_data(db_session)
        events = await search_events(db_session, days=30)
        assert len(events) == 5

    async def test_should_combine_filters(self, db_session):
        await _seed_audit_data(db_session)
        events = await search_events(db_session, days=30, event_type="tool_call")
        assert len(events) == 1
        assert events[0].event_type == "tool_call"

    async def test_should_respect_limit(self, db_session):
        await _seed_audit_data(db_session)
        events = await search_events(db_session, days=30, limit=2)
        assert len(events) == 2


# ---------------------------------------------------------------------------
# Decision backward trace
# ---------------------------------------------------------------------------


class TestDecisionTrace:
    async def test_should_build_grouped_trace(self, db_session):
        ids = await _seed_audit_data(db_session)
        trace = await get_decision_trace(db_session, ids["dec_denied_id"])

        assert trace is not None
        assert trace["decision_id"] == ids["dec_denied_id"]
        assert trace["decision_type"] == "denied"
        assert trace["rationale"] == "High DTI"
        assert trace["ai_agreement"] is True
        assert trace["denial_reasons"] == ["High DTI", "Insufficient reserves"]
        assert trace["total_events"] == 2
        assert "stage_transition" in trace["events_by_type"]
        assert "decision" in trace["events_by_type"]

    async def test_should_return_none_for_unknown_decision(self, db_session):
        trace = await get_decision_trace(db_session, 999999)
        assert trace is None


# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------


class TestAuditExport:
    async def test_should_export_json_for_application(self, db_session):
        ids = await _seed_audit_data(db_session)
        content, media_type = await export_events(
            db_session,
            fmt="json",
            application_id=ids["app1_id"],
        )
        assert media_type == "application/json"
        data = json.loads(content)
        assert len(data) == 3
        assert all(r["application_id"] == ids["app1_id"] for r in data)

    async def test_should_export_csv_with_headers(self, db_session):
        ids = await _seed_audit_data(db_session)
        content, media_type = await export_events(
            db_session,
            fmt="csv",
            application_id=ids["app1_id"],
        )
        assert media_type == "text/csv"
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
        assert len(rows) == 3
        assert "event_id" in rows[0]
        assert "prev_hash" in rows[0]

    async def test_should_filter_export_by_days(self, db_session):
        await _seed_audit_data(db_session)
        content, _ = await export_events(db_session, fmt="json", days=30)
        data = json.loads(content)
        assert len(data) == 5
