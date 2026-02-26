# This project was developed with assistance from AI tools.
"""Tests for rate lock status service, endpoint, and agent tool."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.borrower_tools import rate_lock_status
from src.schemas.rate_lock import RateLockResponse
from src.services.rate_lock import get_rate_lock_status

# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _state(user_id="sarah-uuid", role="borrower"):
    return {"user_id": user_id, "user_role": role}


def _mock_rate_lock(
    locked_rate=6.875,
    lock_date=None,
    expiration_date=None,
    is_active=True,
):
    """Create a mock RateLock ORM object."""
    rl = MagicMock()
    rl.locked_rate = locked_rate
    rl.lock_date = lock_date or datetime.now(UTC) - timedelta(days=10)
    rl.expiration_date = expiration_date or datetime.now(UTC) + timedelta(days=35)
    rl.is_active = is_active
    rl.created_at = datetime.now(UTC)
    return rl


# ---------------------------------------------------------------------------
# Service: get_rate_lock_status
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_service_returns_none_for_out_of_scope():
    """No application found -> None."""
    session = AsyncMock()
    # Application query returns None
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 999)
    assert result is None


@pytest.mark.asyncio
async def test_service_returns_none_status_when_no_lock():
    """Application exists but no rate lock."""
    session = AsyncMock()

    # First call: application found
    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    # Second call: no rate lock
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = None

    session.execute.side_effect = [app_result, lock_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 1)
    assert result["status"] == "none"
    assert result["application_id"] == 1


@pytest.mark.asyncio
async def test_service_returns_active_with_days_remaining():
    """Active rate lock with days remaining."""
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    rl = _mock_rate_lock(
        locked_rate=6.5,
        expiration_date=datetime.now(UTC) + timedelta(days=20),
    )
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = rl

    session.execute.side_effect = [app_result, lock_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 1)
    assert result["status"] == "active"
    assert result["locked_rate"] == 6.5
    assert result["days_remaining"] >= 19
    assert result["is_urgent"] is False


@pytest.mark.asyncio
async def test_service_marks_urgent_within_7_days():
    """Rate lock expiring in 5 days should be urgent."""
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    rl = _mock_rate_lock(expiration_date=datetime.now(UTC) + timedelta(days=5))
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = rl

    session.execute.side_effect = [app_result, lock_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 1)
    assert result["status"] == "active"
    assert result["is_urgent"] is True


@pytest.mark.asyncio
async def test_service_returns_expired_when_past_expiration():
    """Rate lock past expiration date should be expired."""
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    rl = _mock_rate_lock(
        expiration_date=datetime.now(UTC) - timedelta(days=2),
        is_active=True,  # DB still says active but date is past
    )
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = rl

    session.execute.side_effect = [app_result, lock_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 1)
    assert result["status"] == "expired"
    assert result["days_remaining"] == 0


@pytest.mark.asyncio
async def test_service_returns_expired_when_is_active_false():
    """Rate lock with is_active=False should be expired."""
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    rl = _mock_rate_lock(
        expiration_date=datetime.now(UTC) + timedelta(days=10),
        is_active=False,
    )
    lock_result = MagicMock()
    lock_result.scalar_one_or_none.return_value = rl

    session.execute.side_effect = [app_result, lock_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_rate_lock_status(session, user, 1)
    assert result["status"] == "expired"


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------


def test_schema_active():
    resp = RateLockResponse(
        application_id=1,
        status="active",
        locked_rate=6.5,
        lock_date="2026-02-01T00:00:00+00:00",
        expiration_date="2026-03-15T00:00:00+00:00",
        days_remaining=20,
        is_urgent=False,
    )
    assert resp.status == "active"
    assert resp.locked_rate == 6.5


def test_schema_none():
    resp = RateLockResponse(application_id=1, status="none")
    assert resp.locked_rate is None
    assert resp.days_remaining is None


# ---------------------------------------------------------------------------
# Agent tool: rate_lock_status
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_rate_lock_status")
async def test_tool_active_lock(mock_service, mock_session_cls):
    mock_service.return_value = {
        "application_id": 1,
        "status": "active",
        "locked_rate": 6.875,
        "lock_date": "2026-02-15T00:00:00+00:00",
        "expiration_date": "2026-03-25T00:00:00+00:00",
        "days_remaining": 25,
        "is_urgent": False,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await rate_lock_status.ainvoke({"application_id": 1, "state": _state()})

    assert "Active" in result
    assert "6.875%" in result
    assert "25" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_rate_lock_status")
async def test_tool_no_lock(mock_service, mock_session_cls):
    mock_service.return_value = {
        "application_id": 1,
        "status": "none",
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await rate_lock_status.ainvoke({"application_id": 1, "state": _state()})

    assert "does not have a rate lock" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_rate_lock_status")
async def test_tool_expired_lock(mock_service, mock_session_cls):
    mock_service.return_value = {
        "application_id": 1,
        "status": "expired",
        "locked_rate": 7.0,
        "lock_date": "2026-01-01T00:00:00+00:00",
        "expiration_date": "2026-02-01T00:00:00+00:00",
        "days_remaining": 0,
        "is_urgent": False,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await rate_lock_status.ainvoke({"application_id": 1, "state": _state()})

    assert "Expired" in result
    assert "expired" in result.lower()


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_rate_lock_status")
async def test_tool_urgent_lock(mock_service, mock_session_cls):
    mock_service.return_value = {
        "application_id": 1,
        "status": "active",
        "locked_rate": 6.5,
        "lock_date": "2026-02-01T00:00:00+00:00",
        "expiration_date": "2026-02-28T00:00:00+00:00",
        "days_remaining": 2,
        "is_urgent": True,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await rate_lock_status.ainvoke({"application_id": 1, "state": _state()})

    assert "Urgent" in result
    assert "2 days" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_rate_lock_status")
async def test_tool_not_found(mock_service, mock_session_cls):
    mock_service.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await rate_lock_status.ainvoke({"application_id": 999, "state": _state()})

    assert "not found" in result
