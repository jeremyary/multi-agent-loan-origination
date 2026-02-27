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
    clear_condition,
    get_condition_summary,
    get_conditions,
    issue_condition,
    link_document_to_condition,
    respond_to_condition,
    return_condition,
    review_condition,
    waive_condition,
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


# ---------------------------------------------------------------------------
# Service: issue_condition
# ---------------------------------------------------------------------------


def _mock_app(stage="underwriting"):
    """Create a mock application with the given stage."""
    from db.enums import ApplicationStage

    app = MagicMock()
    app.stage = ApplicationStage(stage)
    app.id = 100
    return app


def _mock_condition_obj(
    id=1,
    description="Verify employment",
    severity="prior_to_approval",
    status="open",
    response_text=None,
    issued_by="uw-maria",
    cleared_by=None,
    due_date=None,
    iteration_count=0,
    waiver_rationale=None,
):
    """Create a mock Condition ORM object for lifecycle tests."""
    from db.enums import ConditionSeverity, ConditionStatus

    c = MagicMock()
    c.id = id
    c.description = description
    c.severity = ConditionSeverity(severity)
    c.status = ConditionStatus(status)
    c.response_text = response_text
    c.issued_by = issued_by
    c.cleared_by = cleared_by
    c.due_date = due_date
    c.iteration_count = iteration_count
    c.waiver_rationale = waiver_rationale
    c.application_id = 100
    return c


def _uw_user():
    """Create a mock underwriter UserContext."""
    user = MagicMock()
    user.user_id = "uw-maria"
    user.role = MagicMock()
    user.role.value = "underwriter"
    user.data_scope = MagicMock()
    return user


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_issue_condition_out_of_scope(mock_get_app, mock_audit):
    """issue_condition returns None when application not found."""
    mock_get_app.return_value = None
    session = AsyncMock()

    result = await issue_condition(
        session,
        _uw_user(),
        999,
        "Need pay stubs",
        MagicMock(),
        None,
    )
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_issue_condition_wrong_stage(mock_get_app, mock_audit):
    """issue_condition returns error when app is in wrong stage."""
    mock_get_app.return_value = _mock_app(stage="application")
    session = AsyncMock()

    from db.enums import ConditionSeverity

    result = await issue_condition(
        session,
        _uw_user(),
        100,
        "Need pay stubs",
        ConditionSeverity.PRIOR_TO_DOCS,
        None,
    )
    assert result is not None
    assert "error" in result
    assert "underwriting" in result["error"].lower() or "conditional" in result["error"].lower()


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_issue_condition_happy_path(mock_get_app, mock_audit):
    """issue_condition creates a condition in UNDERWRITING stage."""
    mock_get_app.return_value = _mock_app(stage="underwriting")
    session = AsyncMock()

    from db.enums import ConditionSeverity

    # After commit+refresh, the mock condition should have an id
    async def fake_refresh(obj):
        obj.id = 42
        obj.description = "Need pay stubs"
        obj.severity = ConditionSeverity.PRIOR_TO_DOCS
        obj.status = MagicMock()
        obj.status.value = "open"
        obj.due_date = None

    session.refresh = fake_refresh

    result = await issue_condition(
        session,
        _uw_user(),
        100,
        "Need pay stubs",
        ConditionSeverity.PRIOR_TO_DOCS,
        None,
    )
    assert result is not None
    assert "error" not in result
    assert result["id"] == 42
    assert result["severity"] == "prior_to_docs"
    assert result["status"] == "open"
    session.add.assert_called_once()
    session.commit.assert_awaited_once()
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "condition_issued"


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_issue_condition_with_due_date(mock_get_app, mock_audit):
    """issue_condition records due_date when provided."""
    mock_get_app.return_value = _mock_app(stage="conditional_approval")
    session = AsyncMock()

    from datetime import UTC, datetime

    from db.enums import ConditionSeverity

    due = datetime(2026, 3, 15, tzinfo=UTC)

    async def fake_refresh(obj):
        obj.id = 43
        obj.description = "Updated bank statements"
        obj.severity = ConditionSeverity.PRIOR_TO_CLOSING
        obj.status = MagicMock()
        obj.status.value = "open"
        obj.due_date = due

    session.refresh = fake_refresh

    result = await issue_condition(
        session,
        _uw_user(),
        100,
        "Updated bank statements",
        ConditionSeverity.PRIOR_TO_CLOSING,
        due,
    )
    assert result is not None
    assert result["due_date"] is not None
    assert "2026-03-15" in result["due_date"]


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_issue_condition_audit_event(mock_get_app, mock_audit):
    """issue_condition writes audit with severity and description."""
    mock_get_app.return_value = _mock_app(stage="underwriting")
    session = AsyncMock()

    from db.enums import ConditionSeverity

    async def fake_refresh(obj):
        obj.id = 44
        obj.description = "Verify income"
        obj.severity = ConditionSeverity.PRIOR_TO_APPROVAL
        obj.status = MagicMock()
        obj.status.value = "open"
        obj.due_date = None

    session.refresh = fake_refresh

    await issue_condition(
        session,
        _uw_user(),
        100,
        "Verify income",
        ConditionSeverity.PRIOR_TO_APPROVAL,
        None,
    )
    mock_audit.assert_awaited_once()
    event_data = mock_audit.call_args.kwargs["event_data"]
    assert event_data["severity"] == "prior_to_approval"
    assert event_data["description"] == "Verify income"


# ---------------------------------------------------------------------------
# Service: review_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_review_condition_not_found(mock_fetch, mock_audit):
    """review_condition returns None when condition not found."""
    mock_fetch.return_value = (_mock_app(), None)
    session = AsyncMock()

    result = await review_condition(session, _uw_user(), 100, 999)
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_review_condition_wrong_status(mock_fetch, mock_audit):
    """review_condition returns error when condition is OPEN (not RESPONDED)."""
    cond = _mock_condition_obj(status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await review_condition(session, _uw_user(), 100, 1)
    assert result is not None
    assert "error" in result
    assert "RESPONDED" in result["error"]


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_review_condition_happy_path(mock_fetch, mock_audit):
    """review_condition transitions RESPONDED -> UNDER_REVIEW."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(status="responded")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.UNDER_REVIEW

    session.refresh = fake_refresh

    result = await review_condition(session, _uw_user(), 100, 1)
    assert result is not None
    assert "error" not in result
    assert cond.status == ConditionStatus.UNDER_REVIEW
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "condition_review_started"


# ---------------------------------------------------------------------------
# Service: clear_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_clear_condition_not_found(mock_fetch, mock_audit):
    """clear_condition returns None when condition not found."""
    mock_fetch.return_value = (_mock_app(), None)
    session = AsyncMock()

    result = await clear_condition(session, _uw_user(), 100, 999)
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_clear_condition_wrong_status(mock_fetch, mock_audit):
    """clear_condition returns error when condition is OPEN."""
    cond = _mock_condition_obj(status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await clear_condition(session, _uw_user(), 100, 1)
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_clear_condition_from_responded(mock_fetch, mock_audit):
    """clear_condition transitions RESPONDED -> CLEARED."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(status="responded")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.CLEARED
        obj.cleared_by = "uw-maria"

    session.refresh = fake_refresh

    result = await clear_condition(session, _uw_user(), 100, 1)
    assert result is not None
    assert "error" not in result
    assert result["cleared_by"] == "uw-maria"
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "condition_cleared"


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_clear_condition_from_under_review(mock_fetch, mock_audit):
    """clear_condition transitions UNDER_REVIEW -> CLEARED."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(status="under_review")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.CLEARED
        obj.cleared_by = "uw-maria"

    session.refresh = fake_refresh

    result = await clear_condition(session, _uw_user(), 100, 1)
    assert result is not None
    assert "error" not in result
    assert cond.status == ConditionStatus.CLEARED
    assert cond.cleared_by == "uw-maria"


# ---------------------------------------------------------------------------
# Service: waive_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_not_found(mock_fetch, mock_audit):
    """waive_condition returns None when condition not found."""
    mock_fetch.return_value = (_mock_app(), None)
    session = AsyncMock()

    result = await waive_condition(session, _uw_user(), 100, 999, "Not needed")
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_blocked_prior_to_approval(mock_fetch, mock_audit):
    """waive_condition rejects PRIOR_TO_APPROVAL severity."""
    cond = _mock_condition_obj(severity="prior_to_approval", status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await waive_condition(session, _uw_user(), 100, 1, "Not needed")
    assert result is not None
    assert "error" in result
    assert "PRIOR_TO_CLOSING" in result["error"]


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_blocked_prior_to_docs(mock_fetch, mock_audit):
    """waive_condition rejects PRIOR_TO_DOCS severity."""
    cond = _mock_condition_obj(severity="prior_to_docs", status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await waive_condition(session, _uw_user(), 100, 1, "Not needed")
    assert result is not None
    assert "error" in result


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_succeeds_prior_to_closing(mock_fetch, mock_audit):
    """waive_condition succeeds for PRIOR_TO_CLOSING severity."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(severity="prior_to_closing", status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.WAIVED
        obj.waiver_rationale = "Seller credit covers this"
        obj.cleared_by = "uw-maria"

    session.refresh = fake_refresh

    result = await waive_condition(session, _uw_user(), 100, 1, "Seller credit covers this")
    assert result is not None
    assert "error" not in result
    assert result["waiver_rationale"] == "Seller credit covers this"
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "condition_waived"


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_blocked_terminal(mock_fetch, mock_audit):
    """waive_condition rejects already-cleared conditions."""
    cond = _mock_condition_obj(severity="prior_to_closing", status="cleared")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await waive_condition(session, _uw_user(), 100, 1, "Not needed")
    assert result is not None
    assert "error" in result
    assert "terminal" in result["error"].lower()


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_waive_condition_records_rationale(mock_fetch, mock_audit):
    """waive_condition stores rationale and cleared_by."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(severity="prior_to_funding", status="responded")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.WAIVED
        obj.waiver_rationale = "Immaterial amount"
        obj.cleared_by = "uw-maria"

    session.refresh = fake_refresh

    result = await waive_condition(session, _uw_user(), 100, 1, "Immaterial amount")
    assert result is not None
    assert result["cleared_by"] == "uw-maria"
    audit_data = mock_audit.call_args.kwargs["event_data"]
    assert audit_data["rationale"] == "Immaterial amount"
    assert audit_data["severity"] == "prior_to_funding"


# ---------------------------------------------------------------------------
# Service: return_condition
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_return_condition_not_found(mock_fetch, mock_audit):
    """return_condition returns None when condition not found."""
    mock_fetch.return_value = (_mock_app(), None)
    session = AsyncMock()

    result = await return_condition(session, _uw_user(), 100, 999, "Incomplete docs")
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_return_condition_wrong_status(mock_fetch, mock_audit):
    """return_condition returns error when condition is OPEN."""
    cond = _mock_condition_obj(status="open")
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    result = await return_condition(session, _uw_user(), 100, 1, "Incomplete docs")
    assert result is not None
    assert "error" in result
    assert "UNDER_REVIEW" in result["error"]


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_return_condition_increments_iteration(mock_fetch, mock_audit):
    """return_condition increments iteration_count and returns to OPEN."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(
        status="under_review", iteration_count=1, response_text="First attempt"
    )
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.OPEN
        obj.iteration_count = 2

    session.refresh = fake_refresh

    result = await return_condition(session, _uw_user(), 100, 1, "Missing page 2")
    assert result is not None
    assert "error" not in result
    assert cond.iteration_count == 2
    assert cond.status == ConditionStatus.OPEN
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "condition_returned"


@pytest.mark.asyncio
@patch("src.services.condition.write_audit_event", new_callable=AsyncMock)
@patch("src.services.condition._fetch_condition", new_callable=AsyncMock)
async def test_return_condition_appends_note(mock_fetch, mock_audit):
    """return_condition appends note to response_text."""
    from db.enums import ConditionStatus

    cond = _mock_condition_obj(
        status="under_review", iteration_count=0, response_text="Original response"
    )
    mock_fetch.return_value = (_mock_app(), cond)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.status = ConditionStatus.OPEN

    session.refresh = fake_refresh

    await return_condition(session, _uw_user(), 100, 1, "Need signed copy")
    assert "[Return #1]" in cond.response_text
    assert "Need signed copy" in cond.response_text
    assert "Original response" in cond.response_text


# ---------------------------------------------------------------------------
# Service: get_condition_summary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_get_condition_summary_out_of_scope(mock_get_app):
    """get_condition_summary returns None when application not found."""
    mock_get_app.return_value = None
    session = AsyncMock()

    result = await get_condition_summary(session, _uw_user(), 999)
    assert result is None


@pytest.mark.asyncio
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_get_condition_summary_mixed_counts(mock_get_app):
    """get_condition_summary returns correct counts by status."""
    from db.enums import ConditionStatus

    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = [
        (ConditionStatus.OPEN, 2),
        (ConditionStatus.CLEARED, 3),
        (ConditionStatus.WAIVED, 1),
    ]
    session.execute = AsyncMock(return_value=mock_result)

    result = await get_condition_summary(session, _uw_user(), 100)
    assert result is not None
    assert result["total"] == 6
    assert result["counts"]["open"] == 2
    assert result["counts"]["cleared"] == 3
    assert result["counts"]["waived"] == 1
    assert result["counts"]["responded"] == 0


@pytest.mark.asyncio
@patch("src.services.condition.get_application", new_callable=AsyncMock)
async def test_get_condition_summary_empty(mock_get_app):
    """get_condition_summary returns zero counts when no conditions."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.all.return_value = []
    session.execute = AsyncMock(return_value=mock_result)

    result = await get_condition_summary(session, _uw_user(), 100)
    assert result is not None
    assert result["total"] == 0
    assert result["counts"]["open"] == 0
