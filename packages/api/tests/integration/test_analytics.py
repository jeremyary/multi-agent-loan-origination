# This project was developed with assistance from AI tools.
"""Analytics service integration tests with real PostgreSQL.

Validates that pipeline summary and denial trend queries produce correct
results against a real database -- the class of bugs that mocked session
tests cannot catch (JSONB extraction, GROUP BY, subquery joins, CASE).
"""

import pytest
from db.enums import ApplicationStage, DecisionType, LoanType
from db.models import Application, AuditEvent, Decision

from src.services.analytics import get_denial_trends, get_pipeline_summary

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _seed_analytics_data(db_session):
    """Create a controlled set of applications and decisions.

    Returns dict with IDs for assertions.
    """
    # 3 applications at different stages, different loan types
    app_closed = Application(
        stage=ApplicationStage.CLOSED,
        loan_type=LoanType.CONVENTIONAL_30,
        property_address="100 Closed Ln",
        loan_amount=300000,
        property_value=400000,
    )
    app_uw = Application(
        stage=ApplicationStage.UNDERWRITING,
        loan_type=LoanType.FHA,
        property_address="200 UW Ave",
        loan_amount=250000,
        property_value=300000,
    )
    app_denied = Application(
        stage=ApplicationStage.DENIED,
        loan_type=LoanType.FHA,
        property_address="300 Denied Rd",
        loan_amount=200000,
        property_value=250000,
    )
    db_session.add_all([app_closed, app_uw, app_denied])
    await db_session.flush()

    # Decisions: 1 approved (on closed app), 2 denied (on uw + denied apps)
    dec_approved = Decision(
        application_id=app_closed.id,
        decision_type=DecisionType.APPROVED,
        rationale="Strong financials",
        decided_by="uw-test",
    )
    dec_denied_1 = Decision(
        application_id=app_uw.id,
        decision_type=DecisionType.DENIED,
        rationale="High DTI",
        decided_by="uw-test",
        denial_reasons=["High DTI", "Insufficient reserves"],
    )
    dec_denied_2 = Decision(
        application_id=app_denied.id,
        decision_type=DecisionType.DENIED,
        rationale="Low credit",
        decided_by="uw-test",
        denial_reasons=["Low credit score"],
    )
    db_session.add_all([dec_approved, dec_denied_1, dec_denied_2])
    await db_session.flush()

    # Stage transition audit events for turn time calculation
    # app_closed: APPLICATION -> UNDERWRITING -> CLOSED
    import datetime

    base = datetime.datetime.now(datetime.UTC) - datetime.timedelta(days=30)
    evt_to_uw = AuditEvent(
        event_type="stage_transition",
        user_id="system",
        user_role="system",
        application_id=app_closed.id,
        event_data={"from_stage": "inquiry", "to_stage": "application"},
        timestamp=base,
    )
    evt_to_uw2 = AuditEvent(
        event_type="stage_transition",
        user_id="system",
        user_role="system",
        application_id=app_closed.id,
        event_data={"from_stage": "application", "to_stage": "underwriting"},
        timestamp=base + datetime.timedelta(days=5),
    )
    db_session.add_all([evt_to_uw, evt_to_uw2])
    await db_session.flush()

    return {
        "app_closed_id": app_closed.id,
        "app_uw_id": app_uw.id,
        "app_denied_id": app_denied.id,
    }


# ---------------------------------------------------------------------------
# Pipeline summary
# ---------------------------------------------------------------------------


class TestPipelineSummaryIntegration:
    """Pipeline summary queries against real PostgreSQL."""

    async def test_should_count_stages_from_real_data(self, db_session):
        """Stage counts match seeded applications."""
        await _seed_analytics_data(db_session)

        result = await get_pipeline_summary(db_session, days=365)

        stage_map = {sc.stage: sc.count for sc in result.by_stage}
        assert stage_map["closed"] == 1
        assert stage_map["underwriting"] == 1
        assert stage_map["denied"] == 1
        assert result.total_applications == 3

    async def test_should_compute_pull_through_from_real_data(self, db_session):
        """Pull-through rate computed correctly from real rows."""
        await _seed_analytics_data(db_session)

        result = await get_pipeline_summary(db_session, days=365)

        # 1 closed out of 3 initiated = 33.3%
        assert result.pull_through_rate == pytest.approx(33.3, abs=0.1)

    async def test_should_compute_turn_times_from_audit_events(self, db_session):
        """Turn times derived from real stage_transition audit events."""
        await _seed_analytics_data(db_session)

        result = await get_pipeline_summary(db_session, days=365)

        # We seeded application->underwriting transition with 5-day gap
        uw_turn = next(
            (tt for tt in result.turn_times if tt.to_stage == "underwriting"),
            None,
        )
        assert uw_turn is not None
        assert uw_turn.avg_days == pytest.approx(5.0, abs=0.1)
        assert uw_turn.sample_size == 1


# ---------------------------------------------------------------------------
# Denial trends
# ---------------------------------------------------------------------------


class TestDenialTrendsIntegration:
    """Denial trend queries against real PostgreSQL."""

    async def test_should_compute_denial_rate_from_real_data(self, db_session):
        """Denial rate = 2 denied / 3 total decisions."""
        await _seed_analytics_data(db_session)

        result = await get_denial_trends(db_session, days=365)

        assert result.total_decisions == 3
        assert result.total_denials == 2
        assert result.overall_denial_rate == pytest.approx(66.7, abs=0.1)

    async def test_should_extract_denial_reasons_from_jsonb(self, db_session):
        """Top reasons extracted from real JSONB denial_reasons column."""
        await _seed_analytics_data(db_session)

        result = await get_denial_trends(db_session, days=365)

        reason_names = [r.reason for r in result.top_reasons]
        # All reasons have count < 3, so they all aggregate to "Other"
        # (High DTI: 1, Insufficient reserves: 1, Low credit score: 1)
        assert "Other" in reason_names

    async def test_should_break_down_by_product(self, db_session):
        """By-product breakdown groups denial rates by loan type."""
        await _seed_analytics_data(db_session)

        result = await get_denial_trends(db_session, days=365)

        assert result.by_product is not None
        # CONVENTIONAL_30: 1 decision, 0 denials -> 0%
        assert result.by_product.get("conventional_30") == 0.0
        # FHA: 2 decisions, 2 denials -> 100%
        assert result.by_product.get("fha") == 100.0

    async def test_should_filter_by_product(self, db_session):
        """Product filter restricts to decisions on that loan type."""
        await _seed_analytics_data(db_session)

        result = await get_denial_trends(db_session, days=365, product="fha")

        assert result.total_decisions == 2
        assert result.total_denials == 2
        assert result.overall_denial_rate == 100.0
        assert result.by_product is None  # omitted when filtered

    async def test_should_include_trend_points(self, db_session):
        """Trend includes at least one period with correct totals."""
        await _seed_analytics_data(db_session)

        result = await get_denial_trends(db_session, days=365)

        assert len(result.trend) >= 1
        total_from_trend = sum(p.total_decided for p in result.trend)
        assert total_from_trend == 3
