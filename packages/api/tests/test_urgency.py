# This project was developed with assistance from AI tools.
"""Tests for urgency calculation service."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.schemas.urgency import UrgencyIndicator, UrgencyLevel
from src.services.urgency import EXPECTED_STAGE_DAYS, compute_urgency

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

NOW = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)


def _mock_app(
    app_id=101,
    stage="application",
    updated_at=None,
):
    """Build a mock Application ORM object."""
    from db.enums import ApplicationStage

    app = MagicMock()
    app.id = app_id
    app.stage = ApplicationStage(stage)
    app.updated_at = updated_at or NOW
    return app


def _mock_rate_lock(app_id=101, expiration_days=30, is_active=True):
    """Build a mock RateLock ORM object."""
    rl = MagicMock()
    rl.application_id = app_id
    rl.expiration_date = NOW + timedelta(days=expiration_days)
    rl.is_active = is_active
    rl.created_at = NOW - timedelta(days=10)
    return rl


def _mock_session(rate_locks=None, condition_rows=None, doc_rows=None):
    """Build an AsyncMock session with side_effect for 3 batch queries.

    The urgency service runs 3 sequential queries:
    1. Rate locks (scalars().all())
    2. Condition counts (rows with application_id + cnt)
    3. Oldest pending docs (rows with application_id + oldest)
    """
    session = AsyncMock()

    # Result 1: rate locks
    rl_result = MagicMock()
    rl_result.scalars.return_value.all.return_value = rate_locks or []

    # Result 2: condition counts
    cond_result = MagicMock()
    cond_result.__iter__ = MagicMock(return_value=iter(condition_rows or []))

    # Result 3: oldest pending docs
    doc_result = MagicMock()
    doc_result.__iter__ = MagicMock(return_value=iter(doc_rows or []))

    session.execute = AsyncMock(side_effect=[rl_result, cond_result, doc_result])
    return session


def _cond_row(app_id, cnt):
    """Mock a row from the condition count query."""
    row = MagicMock()
    row.application_id = app_id
    row.cnt = cnt
    return row


def _doc_row(app_id, oldest):
    """Mock a row from the oldest pending doc query."""
    row = MagicMock()
    row.application_id = app_id
    row.oldest = oldest
    return row


# ---------------------------------------------------------------------------
# Rate lock urgency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_lock_expiring_in_2_days_is_critical():
    app = _mock_app()
    rl = _mock_rate_lock(expiration_days=2)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.CRITICAL
    assert any("Rate lock expires" in f for f in result[101].factors)


@pytest.mark.asyncio
async def test_rate_lock_expiring_in_5_days_is_high():
    app = _mock_app()
    rl = _mock_rate_lock(expiration_days=5)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.HIGH
    assert any("Rate lock expires" in f for f in result[101].factors)


@pytest.mark.asyncio
async def test_rate_lock_expiring_in_3_days_is_critical():
    app = _mock_app()
    rl = _mock_rate_lock(expiration_days=3)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.CRITICAL


@pytest.mark.asyncio
async def test_rate_lock_expiring_in_10_days_no_urgency():
    app = _mock_app()
    rl = _mock_rate_lock(expiration_days=10)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    # No rate lock factor, but stage timing may contribute
    assert not any("Rate lock" in f for f in result[101].factors)


# ---------------------------------------------------------------------------
# Stage timing urgency
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_stage_overdue_by_8_days_is_critical():
    expected = EXPECTED_STAGE_DAYS.get("application", 7)
    updated_at = NOW - timedelta(days=expected + 8)
    app = _mock_app(updated_at=updated_at)
    session = _mock_session()

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.CRITICAL
    assert any("overdue" in f for f in result[101].factors)


@pytest.mark.asyncio
async def test_stage_overdue_by_5_days_is_high():
    expected = EXPECTED_STAGE_DAYS.get("application", 7)
    updated_at = NOW - timedelta(days=expected + 5)
    app = _mock_app(updated_at=updated_at)
    session = _mock_session()

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.HIGH
    assert any("overdue" in f for f in result[101].factors)


@pytest.mark.asyncio
async def test_stage_at_80_percent_is_medium():
    """Stage at exactly 80% of expected days -> MEDIUM."""
    # Processing has 5 expected days; 80% = 4 days
    updated_at = NOW - timedelta(days=4)
    app = _mock_app(stage="processing", updated_at=updated_at)
    session = _mock_session()

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.MEDIUM
    assert any("expected days" in f for f in result[101].factors)


# ---------------------------------------------------------------------------
# Multiple factors -- highest wins
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multiple_factors_highest_wins():
    """Rate lock Critical + stage Medium -> overall Critical."""
    updated_at = NOW - timedelta(days=4)  # 80% of processing (5 days)
    app = _mock_app(stage="processing", updated_at=updated_at)
    rl = _mock_rate_lock(expiration_days=2)  # Critical
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.CRITICAL
    assert len(result[101].factors) >= 2


# ---------------------------------------------------------------------------
# No factors -> Normal
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_no_factors_returns_normal():
    app = _mock_app(updated_at=NOW)  # Just entered stage
    session = _mock_session()

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.NORMAL
    assert result[101].factors == []


# ---------------------------------------------------------------------------
# Pending documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_pending_doc_over_48_hours_is_high():
    app = _mock_app(updated_at=NOW)
    oldest = NOW - timedelta(hours=72)
    session = _mock_session(doc_rows=[_doc_row(101, oldest)])

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.HIGH
    assert any("Document request pending" in f for f in result[101].factors)


@pytest.mark.asyncio
async def test_pending_doc_under_48_hours_no_factor():
    app = _mock_app(updated_at=NOW)
    oldest = NOW - timedelta(hours=24)
    session = _mock_session(doc_rows=[_doc_row(101, oldest)])

    result = await compute_urgency(session, [app], now=NOW)

    assert not any("Document request" in f for f in result[101].factors)


# ---------------------------------------------------------------------------
# Open conditions with rate lock
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_open_conditions_with_closing_lock_is_critical():
    app = _mock_app(updated_at=NOW)
    rl = _mock_rate_lock(expiration_days=4)
    session = _mock_session(
        rate_locks=[rl],
        condition_rows=[_cond_row(101, 3)],
    )

    result = await compute_urgency(session, [app], now=NOW)

    assert result[101].level == UrgencyLevel.CRITICAL
    assert any("open condition" in f for f in result[101].factors)


# ---------------------------------------------------------------------------
# Empty input
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_empty_applications_returns_empty_dict():
    session = AsyncMock()
    result = await compute_urgency(session, [], now=NOW)
    assert result == {}


# ---------------------------------------------------------------------------
# Batch: multiple applications
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_batch_computes_per_application():
    app_a = _mock_app(app_id=1, updated_at=NOW)
    app_b = _mock_app(app_id=2, updated_at=NOW - timedelta(days=20))

    rl = _mock_rate_lock(app_id=1, expiration_days=2)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app_a, app_b], now=NOW)

    assert result[1].level == UrgencyLevel.CRITICAL  # rate lock
    assert result[2].level == UrgencyLevel.CRITICAL  # stage overdue


# ---------------------------------------------------------------------------
# Factors list contains human-readable strings
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_factors_are_human_readable():
    app = _mock_app(updated_at=NOW - timedelta(days=20))
    rl = _mock_rate_lock(expiration_days=2)
    session = _mock_session(rate_locks=[rl])

    result = await compute_urgency(session, [app], now=NOW)

    for factor in result[101].factors:
        assert isinstance(factor, str)
        assert len(factor) > 10  # Non-trivial description


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_urgency_indicator_schema():
    indicator = UrgencyIndicator(
        level=UrgencyLevel.HIGH,
        factors=["Rate lock expires in 5 days"],
        days_in_stage=3,
        expected_stage_days=7,
    )
    assert indicator.level == UrgencyLevel.HIGH
    assert len(indicator.factors) == 1
    assert indicator.days_in_stage == 3


def test_urgency_level_values():
    assert UrgencyLevel.CRITICAL.value == "critical"
    assert UrgencyLevel.HIGH.value == "high"
    assert UrgencyLevel.MEDIUM.value == "medium"
    assert UrgencyLevel.NORMAL.value == "normal"
