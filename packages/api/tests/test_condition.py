# This project was developed with assistance from AI tools.
"""Tests for condition service, endpoints, and agent tools."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.agents.borrower_tools import (
    check_condition_satisfaction,
    list_conditions,
    respond_to_condition_tool,
)
from src.schemas.condition import ConditionItem, ConditionListResponse, ConditionRespondRequest
from src.services.condition import (
    check_condition_documents,
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
    from src.schemas import Pagination

    resp = ConditionListResponse(
        data=[
            ConditionItem(id=1, description="Verify employment"),
            ConditionItem(id=2, description="Bank statements"),
        ],
        pagination=Pagination(total=2, offset=0, limit=20, has_more=False),
    )
    assert resp.pagination.total == 2
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
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
async def test_respond_to_condition_records_response(mock_audit):
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
    user.user_id = "sarah-uuid"
    user.role = MagicMock()
    user.role.value = "borrower"

    result = await respond_to_condition(session, user, 100, 5, "Gift from my parents")

    assert cond.response_text == "Gift from my parents"
    assert cond.status == ConditionStatus.RESPONDED
    session.commit.assert_awaited_once()
    assert result is not None

    # Verify audit event was written
    mock_audit.assert_awaited_once()
    audit_call = mock_audit.call_args
    assert audit_call.kwargs["event_type"] == "condition_response"
    assert audit_call.kwargs["user_id"] == "sarah-uuid"
    assert audit_call.kwargs["application_id"] == 100
    assert audit_call.kwargs["event_data"]["condition_id"] == 5


# ---------------------------------------------------------------------------
# Service: check_condition_documents
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_check_condition_documents_out_of_scope():
    session = AsyncMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await check_condition_documents(session, user, 999, 1)
    assert result is None


@pytest.mark.asyncio
async def test_check_condition_documents_condition_not_found():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = None

    session.execute.side_effect = [app_result, cond_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await check_condition_documents(session, user, 100, 999)
    assert result is None


@pytest.mark.asyncio
async def test_check_condition_documents_no_documents():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    from db.enums import ConditionStatus

    cond = MagicMock()
    cond.id = 5
    cond.description = "Upload employment verification"
    cond.status = ConditionStatus.RESPONDED
    cond.response_text = "I'll upload it soon"

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = cond

    doc_result = MagicMock()
    doc_result.scalars.return_value.all.return_value = []

    session.execute.side_effect = [app_result, cond_result, doc_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await check_condition_documents(session, user, 100, 5)
    assert result is not None
    assert result["condition_id"] == 5
    assert result["has_documents"] is False
    assert result["response_text"] == "I'll upload it soon"


@pytest.mark.asyncio
async def test_check_condition_documents_with_docs_and_extractions():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    from db.enums import ConditionStatus

    cond = MagicMock()
    cond.id = 3
    cond.description = "Provide signed employment verification"
    cond.status = ConditionStatus.RESPONDED
    cond.response_text = None

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = cond

    # Mock document with quality flags
    doc = MagicMock()
    doc.id = 10
    doc.file_path = "uploads/emp_verification.pdf"
    doc.doc_type = MagicMock()
    doc.doc_type.value = "employment_verification"
    doc.status = MagicMock()
    doc.status.value = "processing_complete"
    doc.quality_flags = "unsigned"
    doc.created_at = MagicMock()

    doc_result = MagicMock()
    doc_result.scalars.return_value.all.return_value = [doc]

    # Mock extraction
    ext = MagicMock()
    ext.field_name = "employer_name"
    ext.field_value = "Acme Corp"
    ext.confidence = 0.95

    ext_result = MagicMock()
    ext_result.scalars.return_value.all.return_value = [ext]

    session.execute.side_effect = [app_result, cond_result, doc_result, ext_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await check_condition_documents(session, user, 100, 3)
    assert result is not None
    assert result["has_documents"] is True
    assert result["has_quality_issues"] is True
    assert len(result["documents"]) == 1
    assert result["documents"][0]["quality_flags"] == ["unsigned"]
    assert result["documents"][0]["extractions"][0]["field"] == "employer_name"


@pytest.mark.asyncio
async def test_check_condition_documents_clean_document():
    session = AsyncMock()

    app_mock = MagicMock()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app_mock

    from db.enums import ConditionStatus

    cond = MagicMock()
    cond.id = 3
    cond.description = "Provide bank statements"
    cond.status = ConditionStatus.RESPONDED
    cond.response_text = None

    cond_result = MagicMock()
    cond_result.scalar_one_or_none.return_value = cond

    doc = MagicMock()
    doc.id = 11
    doc.file_path = "uploads/bank_stmt.pdf"
    doc.doc_type = MagicMock()
    doc.doc_type.value = "bank_statement"
    doc.status = MagicMock()
    doc.status.value = "processing_complete"
    doc.quality_flags = None
    doc.created_at = MagicMock()

    doc_result = MagicMock()
    doc_result.scalars.return_value.all.return_value = [doc]

    ext_result = MagicMock()
    ext_result.scalars.return_value.all.return_value = []

    session.execute.side_effect = [app_result, cond_result, doc_result, ext_result]

    user = MagicMock()
    user.data_scope = MagicMock()

    result = await check_condition_documents(session, user, 100, 3)
    assert result is not None
    assert result["has_documents"] is True
    assert result["has_quality_issues"] is False


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


# ---------------------------------------------------------------------------
# Agent tool: check_condition_satisfaction
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_condition_documents")
async def test_tool_check_satisfaction_with_clean_doc(mock_service, mock_session_cls):
    mock_service.return_value = {
        "condition_id": 3,
        "description": "Provide signed employment verification",
        "status": "responded",
        "response_text": None,
        "documents": [
            {
                "id": 10,
                "file_path": "uploads/emp_letter.pdf",
                "doc_type": "employment_verification",
                "status": "processing_complete",
                "quality_flags": [],
                "extractions": [
                    {"field": "employer_name", "value": "Acme Corp", "confidence": 0.95},
                ],
            },
        ],
        "has_documents": True,
        "has_quality_issues": False,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await check_condition_satisfaction.ainvoke(
        {"application_id": 100, "condition_id": 3, "state": _state()}
    )

    assert "emp_letter.pdf" in result
    assert "employer_name" in result
    assert "look good" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_condition_documents")
async def test_tool_check_satisfaction_with_quality_issues(mock_service, mock_session_cls):
    mock_service.return_value = {
        "condition_id": 3,
        "description": "Provide signed employment verification",
        "status": "responded",
        "response_text": None,
        "documents": [
            {
                "id": 10,
                "file_path": "uploads/emp_letter.pdf",
                "doc_type": "employment_verification",
                "status": "processing_complete",
                "quality_flags": ["unsigned"],
                "extractions": [],
            },
        ],
        "has_documents": True,
        "has_quality_issues": True,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await check_condition_satisfaction.ainvoke(
        {"application_id": 100, "condition_id": 3, "state": _state()}
    )

    assert "quality issues" in result
    assert "unsigned" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_condition_documents")
async def test_tool_check_satisfaction_no_documents(mock_service, mock_session_cls):
    mock_service.return_value = {
        "condition_id": 5,
        "description": "Explain large deposit",
        "status": "responded",
        "response_text": "Gift from parents",
        "documents": [],
        "has_documents": False,
        "has_quality_issues": False,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await check_condition_satisfaction.ainvoke(
        {"application_id": 100, "condition_id": 5, "state": _state()}
    )

    assert "No documents" in result
    assert "text response" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_condition_documents")
async def test_tool_check_satisfaction_not_found(mock_service, mock_session_cls):
    mock_service.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await check_condition_satisfaction.ainvoke(
        {"application_id": 999, "condition_id": 1, "state": _state()}
    )

    assert "not found" in result
