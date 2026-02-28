# This project was developed with assistance from AI tools.
"""Tests for analytics service and endpoints (F12 -- CEO Executive Dashboard)."""

from unittest.mock import AsyncMock, MagicMock

import pytest
from db.enums import ApplicationStage, LoanType

from src.services.analytics import (
    get_denial_trends,
    get_pipeline_summary,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_session():
    """Mock async database session."""
    session = AsyncMock()
    return session


def _mock_execute_results(*results):
    """Build a chain of mock execute() return values.

    Each result can be:
    - A list of tuples (for .all())
    - A scalar value (for .scalar())
    - A single tuple (for .one())
    """
    side_effects = []
    for r in results:
        mock_result = MagicMock()
        if isinstance(r, list):
            mock_result.all.return_value = r
            if r:
                mock_result.one.return_value = r[0]
            mock_result.scalar.return_value = r[0][0] if r and len(r[0]) == 1 else None
        elif isinstance(r, tuple):
            mock_result.one.return_value = r
            mock_result.all.return_value = [r]
            mock_result.scalar.return_value = r[0]
        else:
            mock_result.scalar.return_value = r
            mock_result.all.return_value = []
            mock_result.one.return_value = (r,)
        side_effects.append(mock_result)
    return side_effects


# ---------------------------------------------------------------------------
# Pipeline summary -- service layer
# ---------------------------------------------------------------------------


class TestPipelineSummary:
    """Tests for get_pipeline_summary."""

    @pytest.mark.asyncio
    async def test_should_return_stage_counts(self, mock_session):
        """Pipeline summary includes application count per stage."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                # stage counts
                [
                    (ApplicationStage.INQUIRY, 5),
                    (ApplicationStage.UNDERWRITING, 3),
                    (ApplicationStage.CLOSED, 2),
                ],
                # initiated count
                10,
                # closed count
                2,
                # avg days to close
                45.5,
                # turn time queries (4 transitions, each returns avg + count)
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),
            )
        )

        result = await get_pipeline_summary(mock_session, days=90)

        assert result.total_applications == 10
        assert len(result.by_stage) == 3
        assert result.by_stage[0].stage == "inquiry"
        assert result.by_stage[0].count == 5

    @pytest.mark.asyncio
    async def test_should_calculate_pull_through_rate(self, mock_session):
        """Pull-through rate = closed / initiated * 100."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                [(ApplicationStage.CLOSED, 8)],  # stage counts
                20,  # initiated
                8,  # closed
                30.0,  # avg days
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),  # turn times
            )
        )

        result = await get_pipeline_summary(mock_session, days=90)

        assert result.pull_through_rate == 40.0  # 8/20 * 100

    @pytest.mark.asyncio
    async def test_should_handle_zero_applications(self, mock_session):
        """Empty portfolio returns zero values."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                [],  # no stage counts
                0,  # initiated
                0,  # closed
                None,  # avg days
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),  # turn times
            )
        )

        result = await get_pipeline_summary(mock_session, days=90)

        assert result.total_applications == 0
        assert result.pull_through_rate == 0.0
        assert result.avg_days_to_close is None
        assert result.turn_times == []

    @pytest.mark.asyncio
    async def test_should_include_turn_times_when_data_exists(self, mock_session):
        """Turn times populated when audit events have stage transitions."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                [(ApplicationStage.UNDERWRITING, 3)],  # stage counts
                10,  # initiated
                3,  # closed
                45.0,  # avg days
                (5.2, 3),  # application -> underwriting
                (3.1, 2),  # underwriting -> conditional_approval
                (None, 0),  # conditional_approval -> clear_to_close
                (None, 0),  # clear_to_close -> closed
            )
        )

        result = await get_pipeline_summary(mock_session, days=90)

        assert len(result.turn_times) == 2
        assert result.turn_times[0].from_stage == "application"
        assert result.turn_times[0].to_stage == "underwriting"
        assert result.turn_times[0].avg_days == 5.2
        assert result.turn_times[0].sample_size == 3

    @pytest.mark.asyncio
    async def test_should_respect_time_range(self, mock_session):
        """Time range is passed through to the response."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                [],  # stages
                0,
                0,
                None,  # counts
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),
            )
        )

        result = await get_pipeline_summary(mock_session, days=30)

        assert result.time_range_days == 30


# ---------------------------------------------------------------------------
# Denial trends -- service layer
# ---------------------------------------------------------------------------


class TestDenialTrends:
    """Tests for get_denial_trends."""

    @pytest.mark.asyncio
    async def test_should_calculate_overall_denial_rate(self, mock_session):
        """Overall denial rate = denials / total decisions * 100."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                15,  # total decisions
                3,  # total denials
                [],  # trend (empty)
                [],  # denial reasons (empty)
                [],  # by product (empty)
            )
        )

        result = await get_denial_trends(mock_session, days=90)

        assert result.overall_denial_rate == 20.0  # 3/15 * 100
        assert result.total_decisions == 15
        assert result.total_denials == 3

    @pytest.mark.asyncio
    async def test_should_handle_zero_decisions(self, mock_session):
        """Zero decisions yields 0% denial rate."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                0,  # total decisions
                0,  # total denials
                [],  # trend
                [],  # reasons
                [],  # by product
            )
        )

        result = await get_denial_trends(mock_session, days=90)

        assert result.overall_denial_rate == 0.0
        assert result.total_decisions == 0
        assert result.trend == []
        assert result.top_reasons == []

    @pytest.mark.asyncio
    async def test_should_compute_trend_points(self, mock_session):
        """Trend includes period-by-period denial rates."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                10,  # total decisions
                2,  # total denials
                # trend data: (period, total, denials)
                [("2026-01", 5, 1), ("2026-02", 5, 1)],
                [],  # reasons
                [],  # by product
            )
        )

        result = await get_denial_trends(mock_session, days=90)

        assert len(result.trend) == 2
        assert result.trend[0].period == "2026-01"
        assert result.trend[0].denial_rate == 20.0
        assert result.trend[0].denial_count == 1
        assert result.trend[0].total_decided == 5

    @pytest.mark.asyncio
    async def test_should_aggregate_rare_reasons_to_other(self, mock_session):
        """Denial reasons with < 3 occurrences aggregated to 'Other'."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                20,  # total decisions
                10,  # total denials
                [],  # trend
                # denial_reasons JSONB values
                [
                    (["High DTI"],),
                    (["High DTI"],),
                    (["High DTI"],),
                    (["High DTI"],),
                    (["High DTI"],),
                    (["Low credit score"],),
                    (["Low credit score"],),
                    (["Low credit score"],),
                    (["Rare reason A"],),
                    (["Rare reason B"],),
                ],
                [],  # by product
            )
        )

        result = await get_denial_trends(mock_session, days=90)

        reason_names = [r.reason for r in result.top_reasons]
        assert "High DTI" in reason_names
        assert "Low credit score" in reason_names
        assert "Other" in reason_names
        assert "Rare reason A" not in reason_names
        assert "Rare reason B" not in reason_names

    @pytest.mark.asyncio
    async def test_should_include_denial_by_product(self, mock_session):
        """By-product breakdown included when no product filter applied."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                10,  # total decisions
                3,  # total denials
                [],  # trend
                [],  # reasons
                # by product: (loan_type, total, denials)
                [
                    (LoanType.CONVENTIONAL_30, 6, 1),
                    (LoanType.FHA, 4, 2),
                ],
            )
        )

        result = await get_denial_trends(mock_session, days=90)

        assert result.by_product is not None
        assert result.by_product["conventional_30"] == 16.7  # 1/6 * 100
        assert result.by_product["fha"] == 50.0  # 2/4 * 100

    @pytest.mark.asyncio
    async def test_should_omit_by_product_when_filtered(self, mock_session):
        """By-product breakdown omitted when a product filter is applied."""
        mock_session.execute = AsyncMock(
            side_effect=_mock_execute_results(
                5,  # total decisions
                1,  # total denials
                [],  # trend
                [],  # reasons
            )
        )

        result = await get_denial_trends(mock_session, days=90, product="fha")

        assert result.by_product is None


# ---------------------------------------------------------------------------
# REST endpoint tests (functional, with mock DB)
# ---------------------------------------------------------------------------


class TestAnalyticsEndpoints:
    """Tests for /api/analytics/* route layer."""

    def test_should_reject_invalid_days(self, client):
        """GET /api/analytics/pipeline?days=0 returns 422."""
        response = client.get("/api/analytics/pipeline", params={"days": 0})
        assert response.status_code == 422

    def test_should_reject_days_over_max(self, client):
        """GET /api/analytics/pipeline?days=999 returns 422."""
        response = client.get("/api/analytics/pipeline", params={"days": 999})
        assert response.status_code == 422


class TestAnalyticsEndpointsFunctional:
    """Functional tests for analytics endpoints with mock DB sessions.

    Uses the same pattern as tests/functional/ -- override get_db with a mock
    session and get_current_user with a CEO persona.
    """

    @pytest.fixture(autouse=True)
    def _clean(self):
        from src.main import app

        yield
        app.dependency_overrides.clear()

    def _make_client(self, mock_results):
        """Build a TestClient with CEO persona and mock DB."""
        from fastapi.testclient import TestClient

        from src.main import app
        from tests.functional.mock_db import configure_app_for_persona
        from tests.functional.personas import ceo

        session = AsyncMock()
        session.execute = AsyncMock(side_effect=mock_results)
        configure_app_for_persona(app, ceo(), session)
        return TestClient(app)

    def test_should_return_pipeline_summary(self):
        """GET /api/analytics/pipeline returns 200 with pipeline data."""
        client = self._make_client(
            _mock_execute_results(
                [(ApplicationStage.INQUIRY, 3)],  # stage counts
                5,
                1,
                20.0,  # initiated, closed, avg days
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),  # turn times
            )
        )
        response = client.get("/api/analytics/pipeline")
        assert response.status_code == 200
        body = response.json()
        assert body["total_applications"] == 3
        assert "by_stage" in body
        assert "pull_through_rate" in body
        assert "turn_times" in body
        assert body["time_range_days"] == 90

    def test_should_accept_days_parameter(self):
        """GET /api/analytics/pipeline?days=30 respects time range."""
        client = self._make_client(
            _mock_execute_results(
                [],  # stages
                0,
                0,
                None,
                (None, 0),
                (None, 0),
                (None, 0),
                (None, 0),
            )
        )
        response = client.get("/api/analytics/pipeline", params={"days": 30})
        assert response.status_code == 200
        assert response.json()["time_range_days"] == 30

    def test_should_return_denial_trends(self):
        """GET /api/analytics/denial-trends returns 200 with denial data."""
        client = self._make_client(
            _mock_execute_results(
                10,
                2,  # total decisions, denials
                [("2026-02", 10, 2)],  # trend
                [],  # reasons
                [(LoanType.FHA, 5, 1)],  # by product
            )
        )
        response = client.get("/api/analytics/denial-trends")
        assert response.status_code == 200
        body = response.json()
        assert "overall_denial_rate" in body
        assert "total_decisions" in body
        assert "trend" in body
        assert "top_reasons" in body
        assert isinstance(body["trend"], list)

    def test_should_filter_denials_by_product(self):
        """GET /api/analytics/denial-trends?product=fha omits by_product."""
        client = self._make_client(
            _mock_execute_results(
                5,
                1,  # total decisions, denials
                [],  # trend
                [],  # reasons
                # no by_product query when filtered
            )
        )
        response = client.get("/api/analytics/denial-trends", params={"product": "fha"})
        assert response.status_code == 200
        assert response.json()["by_product"] is None

    def test_should_deny_non_ceo_roles(self):
        """GET /api/analytics/pipeline returns 403 for borrower role."""
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
            response = client.get("/api/analytics/pipeline")
            assert response.status_code == 403
        finally:
            settings.AUTH_DISABLED = original
