# This project was developed with assistance from AI tools.
"""Tests for condition service, endpoints, and agent tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.borrower_tools import list_conditions, respond_to_condition_tool
from src.schemas.condition import ConditionItem, ConditionListResponse, ConditionRespondRequest
from src.services.condition import (
    get_conditions,
    link_document_to_condition,
    respond_to_condition,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(user_id="sarah-uuid", role="borrower"):
    return {"user_id": user_id, "user_role": role}


def _mock_condition(
    id=1,
    description="Verify employment",
    severity="prior_to_approval",
    status="open",
    response_text=None,
    issued_by="maria-uuid",
    application_id=100,
):
    c = MagicMock()
    c.id = id
    c.description = description
    c.severity = MagicMock()
    c.severity.value = severity
    c.status = MagicMock()
    c.status.value = status
    c.response_text = response_text
    c.issued_by = issued_by
    c.application_id = application_id
    c.created_at = MagicMock()
    c.created_at.isoformat.return_value = "2026-02-20T00:00:00+00:00"
    return c


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_condition_item_schema():
    item = ConditionItem(
        id=1,
        description="Verify employment",
        severity="prior_to_approval",
        status="open",
    )
    assert item.id == 1
    assert item.status == "open"


def test_condition_list_response_schema():
    resp = ConditionListResponse(
        data=[
            ConditionItem(id=1, description="Verify employment"),
            ConditionItem(id=2, description="Bank statements"),
        ],
        count=2,
    )
    assert resp.count == 2
    assert len(resp.data) == 2


def test_condition_respond_request_schema():
    req = ConditionRespondRequest(response_text="Gift from parents for down payment")
    assert req.response_text == "Gift from parents for down payment"


# ---------------------------------------------------------------------------
# Service: get_conditions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_conditions_returns_none_for_out_of_scope():
    session = AsyncMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_conditions(session, user, 999)
    assert result is None


@pytest.mark.asyncio
async def test_get_conditions_returns_empty_list_when_no_conditions():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    cond_result = MagicMock()
    cond_result.scalars.return_value.all.return_value = []

    session.execute.side_effect = [app_result, cond_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_conditions(session, user, 100)
    assert result == []


@pytest.mark.asyncio
async def test_get_conditions_returns_condition_list():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    c1 = _mock_condition(id=1, description="Verify employment", status="open")
    c2 = _mock_condition(
        id=2,
        description="Bank statements",
        status="responded",
        response_text="Uploaded both months",
    )
    cond_result = MagicMock()
    cond_result.scalars.return_value.all.return_value = [c1, c2]

    session.execute.side_effect = [app_result, cond_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await get_conditions(session, user, 100)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["status"] == "open"
    assert result[1]["response_text"] == "Uploaded both months"


# ---------------------------------------------------------------------------
# Service: respond_to_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_respond_to_condition_out_of_scope():
    session = AsyncMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await respond_to_condition(session, user, 999, 1, "my response")
    assert result is None


@pytest.mark.asyncio
async def test_respond_to_condition_condition_not_found():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = None

    session.execute.side_effect = [app_result, cond_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await respond_to_condition(session, user, 100, 999, "my response")
    assert result is None


@pytest.mark.asyncio
async def test_respond_to_condition_records_response():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    from db.enums import ConditionStatus

    cond = MagicMock()
    cond.id = 5
    cond.description = "Explain large deposit"
    cond.status = ConditionStatus.OPEN
    cond.response_text = None

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = cond

    session.execute.side_effect = [app_result, cond_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await respond_to_condition(session, user, 100, 5, "Gift from my parents")

    assert cond.response_text == "Gift from my parents"
    assert cond.status == ConditionStatus.RESPONDED
    session.commit.assert_awaited_once()
    assert result is not None


# ---------------------------------------------------------------------------
# Service: link_document_to_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_link_document_to_condition_out_of_scope():
    session = AsyncMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await link_document_to_condition(session, user, 999, 1, 1)
    assert result is None


@pytest.mark.asyncio
async def test_link_document_to_condition_success():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    from db.enums import ConditionStatus

    cond = MagicMock()
    cond.id = 3
    cond.description = "Upload employment verification"
    cond.status = ConditionStatus.OPEN

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = cond

    doc = MagicMock()
    doc.id = 10
    doc.condition_id = None

    doc_result = MagicMock()
    doc_result.scalar_one_or_none.return_value = doc

    session.execute.side_effect = [app_result, cond_result, doc_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await link_document_to_condition(session, user, 100, 3, 10)

    assert doc.condition_id == 3
    assert cond.status == ConditionStatus.RESPONDED
    session.commit.assert_awaited_once()
    assert result is not None
    assert result["document_id"] == 10


# ---------------------------------------------------------------------------
# Agent tool: list_conditions
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_conditions")
async def test_tool_list_conditions_with_open(mock_service, mock_session_cls):
    mock_service.return_value = [
        {
            "id": 1,
            "description": "Verify employment",
            "severity": "prior_to_approval",
            "status": "open",
            "response_text": None,
            "issued_by": "maria-uuid",
            "created_at": "2026-02-20T00:00:00+00:00",
        },
        {
            "id": 2,
            "description": "Bank statements",
            "severity": "prior_to_approval",
            "status": "responded",
            "response_text": "Uploaded both months",
            "issued_by": "maria-uuid",
            "created_at": "2026-02-20T00:00:00+00:00",
        },
    ]

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await list_conditions.ainvoke({"application_id": 100, "state": _state()})

    assert "Verify employment" in result
    assert "condition #1" in result
    assert "1 condition(s)" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_conditions")
async def test_tool_list_conditions_none_pending(mock_service, mock_session_cls):
    mock_service.return_value = []

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await list_conditions.ainvoke({"application_id": 100, "state": _state()})

    assert "no pending conditions" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_conditions")
async def test_tool_list_conditions_not_found(mock_service, mock_session_cls):
    mock_service.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await list_conditions.ainvoke({"application_id": 999, "state": _state()})

    assert "not found" in result


# ---------------------------------------------------------------------------
# Agent tool: respond_to_condition_tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.respond_to_condition")
async def test_tool_respond_success(mock_service, mock_session_cls):
    mock_service.return_value = {
        "id": 5,
        "description": "Explain large deposit",
        "status": "responded",
        "response_text": "Gift from parents",
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await respond_to_condition_tool.ainvoke(
        {
            "application_id": 100,
            "condition_id": 5,
            "response_text": "Gift from parents",
            "state": _state(),
        }
    )

    assert "Recorded" in result
    assert "condition #5" in result
    assert "underwriter will review" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.respond_to_condition")
async def test_tool_respond_not_found(mock_service, mock_session_cls):
    mock_service.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await respond_to_condition_tool.ainvoke(
        {
            "application_id": 100,
            "condition_id": 999,
            "response_text": "my response",
            "state": _state(),
        }
    )

    assert "not found" in result
