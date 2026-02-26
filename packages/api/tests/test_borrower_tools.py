# This project was developed with assistance from AI tools.
"""Tests for borrower assistant LangGraph tools."""

from datetime import date, timedelta
from unittest.mock import AsyncMock, patch

from db.enums import DocumentType

from src.agents.borrower_tools import (
    _user_context_from_state,
    acknowledge_disclosure,
    application_status,
    disclosure_status,
    document_completeness,
    document_processing_status,
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
# document_processing_status tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.list_documents")
async def test_processing_status_shows_mixed_statuses(mock_list, mock_session_cls):
    """Tool correctly labels processing, complete, and failed documents."""
    from unittest.mock import MagicMock

    from db.enums import DocumentStatus, DocumentType

    docs = []
    for dtype, status in [
        (DocumentType.W2, DocumentStatus.PROCESSING_COMPLETE),
        (DocumentType.PAY_STUB, DocumentStatus.PROCESSING),
        (DocumentType.BANK_STATEMENT, DocumentStatus.PROCESSING_FAILED),
    ]:
        d = MagicMock()
        d.doc_type = dtype
        d.status = status
        docs.append(d)

    mock_list.return_value = (docs, 3)

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await document_processing_status.ainvoke({"application_id": 1, "state": _state()})

    assert "3 document(s)" in result
    assert "Processed successfully" in result
    assert "Processing..." in result
    assert "Processing failed" in result
    assert "1 document(s) still processing" in result
    assert "1 document(s) failed processing" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.list_documents")
async def test_processing_status_no_documents(mock_list, mock_session_cls):
    """Tool reports no documents uploaded when list is empty."""
    mock_list.return_value = ([], 0)

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await document_processing_status.ainvoke({"application_id": 1, "state": _state()})

    assert "No documents have been uploaded" in result


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


# ---------------------------------------------------------------------------
# acknowledge_disclosure tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.write_audit_event")
async def test_acknowledge_disclosure_records_event(mock_write, mock_session_cls):
    mock_write.return_value = AsyncMock()

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await acknowledge_disclosure.ainvoke(
        {
            "application_id": 1,
            "disclosure_id": "loan_estimate",
            "borrower_confirmation": "I acknowledge",
            "state": _state(),
        }
    )

    assert "Loan Estimate" in result
    assert "acknowledged" in result
    mock_write.assert_called_once()
    call_kwargs = mock_write.call_args[1]
    assert call_kwargs["event_type"] == "disclosure_acknowledged"
    assert call_kwargs["application_id"] == 1
    assert call_kwargs["event_data"]["disclosure_id"] == "loan_estimate"
    assert call_kwargs["event_data"]["borrower_confirmation"] == "I acknowledge"


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.write_audit_event")
async def test_acknowledge_disclosure_invalid_id(mock_write, mock_session_cls):
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await acknowledge_disclosure.ainvoke(
        {
            "application_id": 1,
            "disclosure_id": "not_real",
            "borrower_confirmation": "yes",
            "state": _state(),
        }
    )

    assert "Unknown disclosure" in result
    assert "not_real" in result
    mock_write.assert_not_called()


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.write_audit_event")
async def test_acknowledge_disclosure_hmda_notice(mock_write, mock_session_cls):
    mock_write.return_value = AsyncMock()

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await acknowledge_disclosure.ainvoke(
        {
            "application_id": 5,
            "disclosure_id": "hmda_notice",
            "borrower_confirmation": "yes I agree",
            "state": _state(),
        }
    )

    assert "HMDA Notice" in result
    call_kwargs = mock_write.call_args[1]
    assert call_kwargs["event_data"]["disclosure_id"] == "hmda_notice"
    assert call_kwargs["user_id"] == "sarah-uuid"


# ---------------------------------------------------------------------------
# disclosure_status tool
# ---------------------------------------------------------------------------


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_disclosure_status")
async def test_disclosure_status_all_pending(mock_status, mock_session_cls):
    mock_status.return_value = {
        "application_id": 1,
        "all_acknowledged": False,
        "acknowledged": [],
        "pending": [
            "equal_opportunity_notice",
            "hmda_notice",
            "loan_estimate",
            "privacy_notice",
        ],
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await disclosure_status.ainvoke({"application_id": 1, "state": _state()})

    assert "0/4" in result
    assert "Pending:" in result
    assert "Loan Estimate" in result
    assert "Privacy Notice" in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_disclosure_status")
async def test_disclosure_status_all_acknowledged(mock_status, mock_session_cls):
    mock_status.return_value = {
        "application_id": 1,
        "all_acknowledged": True,
        "acknowledged": [
            "equal_opportunity_notice",
            "hmda_notice",
            "loan_estimate",
            "privacy_notice",
        ],
        "pending": [],
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await disclosure_status.ainvoke({"application_id": 1, "state": _state()})

    assert "All required disclosures have been acknowledged" in result
    assert "Acknowledged:" in result
    assert "Pending:" not in result


@patch("src.agents.borrower_tools.SessionLocal")
@patch("src.agents.borrower_tools.get_disclosure_status")
async def test_disclosure_status_partial(mock_status, mock_session_cls):
    mock_status.return_value = {
        "application_id": 1,
        "all_acknowledged": False,
        "acknowledged": ["loan_estimate", "privacy_notice"],
        "pending": ["equal_opportunity_notice", "hmda_notice"],
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await disclosure_status.ainvoke({"application_id": 1, "state": _state()})

    assert "2/4" in result
    assert "Acknowledged:" in result
    assert "Loan Estimate" in result
    assert "Pending:" in result
    assert "HMDA Notice" in result
