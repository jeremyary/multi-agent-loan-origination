# This project was developed with assistance from AI tools.
"""Tests for borrower assistant LangGraph tools."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from db.enums import DocumentType

from src.agents.borrower_tools import (
    _user_context_from_state,
    application_status,
    document_completeness,
    regulatory_deadlines,
)
from src.schemas.completeness import CompletenessResponse, DocumentRequirement
from src.schemas.status import ApplicationStatusResponse, PendingAction, StageInfo

# ---------------------------------------------------------------------------
# Helper: minimal graph state
# ---------------------------------------------------------------------------


def _state(user_id="sarah-uuid", role="borrower"):
    return {"user_id": user_id, "user_role": role}


# ---------------------------------------------------------------------------
# _user_context_from_state
# ---------------------------------------------------------------------------


def test_user_context_builds_borrower_scope():
    ctx = _user_context_from_state(_state())
    assert ctx.user_id == "sarah-uuid"
    assert ctx.role.value == "borrower"
    assert ctx.data_scope.own_data_only is True


def test_user_context_builds_admin_scope():
    ctx = _user_context_from_state(_state(role="admin"))
    assert ctx.data_scope.full_pipeline is True
    assert ctx.data_scope.own_data_only is False


# ---------------------------------------------------------------------------
# document_completeness tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_completeness")
async def test_completeness_tool_formats_missing_docs(mock_check, mock_session_cls):
    mock_check.return_value = CompletenessResponse(
        application_id=1,
        is_complete=False,
        requirements=[
            DocumentRequirement(doc_type=DocumentType.W2, label="W-2 Form", is_provided=True),
            DocumentRequirement(
                doc_type=DocumentType.BANK_STATEMENT,
                label="Bank Statement",
                is_provided=False,
            ),
        ],
        provided_count=1,
        required_count=2,
    )

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await document_completeness.ainvoke({"application_id": 1, "state": _state()})

    assert "Incomplete" in result
    assert "1/2" in result
    assert "W-2 Form: Provided" in result
    assert "Bank Statement: MISSING" in result
    assert "Next step: Upload Bank Statement" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_completeness")
async def test_completeness_tool_not_found(mock_check, mock_session_cls):
    mock_check.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await document_completeness.ainvoke({"application_id": 999, "state": _state()})
    assert "not found" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.check_completeness")
async def test_completeness_tool_shows_quality_flags(mock_check, mock_session_cls):
    mock_check.return_value = CompletenessResponse(
        application_id=1,
        is_complete=True,
        requirements=[
            DocumentRequirement(
                doc_type=DocumentType.W2,
                label="W-2 Form",
                is_provided=True,
                quality_flags=["blurry"],
            ),
        ],
        provided_count=1,
        required_count=1,
    )

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await document_completeness.ainvoke({"application_id": 1, "state": _state()})
    assert "blurry" in result
    assert "Complete" in result


# ---------------------------------------------------------------------------
# application_status tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_application_status")
async def test_status_tool_formats_response(mock_status, mock_session_cls):
    mock_status.return_value = ApplicationStatusResponse(
        application_id=1,
        stage="application",
        stage_info=StageInfo(
            label="Application",
            description="Your application is in progress.",
            next_step="Submit required documents.",
            typical_timeline="Depends on document submission",
        ),
        is_document_complete=False,
        provided_doc_count=2,
        required_doc_count=4,
        open_condition_count=0,
        pending_actions=[
            PendingAction(action_type="upload_document", description="Upload Bank Statement"),
        ],
    )

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await application_status.ainvoke({"application_id": 1, "state": _state()})

    assert "Application" in result
    assert "2/4" in result
    assert "incomplete" in result
    assert "Upload Bank Statement" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_application_status")
async def test_status_tool_not_found(mock_status, mock_session_cls):
    mock_status.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await application_status.ainvoke({"application_id": 999, "state": _state()})
    assert "not found" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_application_status")
async def test_status_tool_shows_conditions(mock_status, mock_session_cls):
    mock_status.return_value = ApplicationStatusResponse(
        application_id=1,
        stage="conditional_approval",
        stage_info=StageInfo(
            label="Conditional Approval",
            description="Conditionally approved.",
            next_step="Clear conditions.",
            typical_timeline="Varies",
        ),
        is_document_complete=True,
        provided_doc_count=4,
        required_doc_count=4,
        open_condition_count=3,
        pending_actions=[
            PendingAction(
                action_type="clear_conditions",
                description="3 underwriting condition(s) to resolve",
            ),
        ],
    )

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await application_status.ainvoke({"application_id": 1, "state": _state()})
    assert "Open conditions: 3" in result
    assert "3 underwriting condition(s)" in result


# ---------------------------------------------------------------------------
# regulatory_deadlines tool
# ---------------------------------------------------------------------------


def test_deadlines_pre_application_stage():
    result = regulatory_deadlines.invoke(
        {"application_date": "2026-01-15", "current_stage": "inquiry"}
    )
    assert "No regulatory deadlines apply yet" in result
    assert "simulated for demonstration" in result


def test_deadlines_active_application():
    past_date = (date.today() - timedelta(days=45)).isoformat()
    result = regulatory_deadlines.invoke(
        {"application_date": past_date, "current_stage": "application"}
    )
    assert "Reg B" in result
    assert "TRID" in result
    assert "simulated for demonstration" in result


def test_deadlines_future_application():
    today = date.today().isoformat()
    result = regulatory_deadlines.invoke({"application_date": today, "current_stage": "processing"})
    assert "Reg B" in result
    assert "days remaining" in result
    assert "TRID" in result


def test_deadlines_invalid_date():
    result = regulatory_deadlines.invoke(
        {"application_date": "not-a-date", "current_stage": "application"}
    )
    assert "Invalid date format" in result
    assert "simulated for demonstration" in result


def test_deadlines_prequalification_stage():
    result = regulatory_deadlines.invoke(
        {"application_date": "2026-02-01", "current_stage": "prequalification"}
    )
    assert "No regulatory deadlines apply yet" in result
