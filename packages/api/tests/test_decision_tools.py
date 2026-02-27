# This project was developed with assistance from AI tools.
"""Tests for decision agent tools."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.decision_tools import (
    uw_draft_adverse_action,
    uw_generate_cd,
    uw_generate_le,
    uw_render_decision,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(user_id="uw-maria", role="underwriter"):
    return {"user_id": user_id, "user_role": role}


def _mock_app(stage="underwriting", id=100):
    from decimal import Decimal

    from db.enums import ApplicationStage, LoanType

    app = MagicMock()
    app.stage = ApplicationStage(stage)
    app.id = id
    app.loan_amount = Decimal("350000")
    app.property_value = Decimal("450000")
    app.loan_type = LoanType.CONVENTIONAL_30
    app.property_address = "123 Main St, Denver, CO"
    app.le_delivery_date = None
    app.cd_delivery_date = None
    app.application_borrowers = []
    return app


def _mock_decision(
    id=1,
    application_id=100,
    decision_type="denied",
    denial_reasons=None,
    credit_score_used=None,
    credit_score_source=None,
    contributing_factors=None,
):
    from db.enums import DecisionType

    d = MagicMock()
    d.id = id
    d.application_id = application_id
    d.decision_type = DecisionType(decision_type)
    d.rationale = "Test rationale"
    d.denial_reasons = json.dumps(denial_reasons) if denial_reasons else None
    d.credit_score_used = credit_score_used
    d.credit_score_source = credit_score_source
    d.contributing_factors = contributing_factors
    return d


# ---------------------------------------------------------------------------
# uw_render_decision
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_approve_success(mock_session_cls, mock_render):
    """uw_render_decision formats approval output."""
    mock_render.return_value = {
        "id": 1,
        "decision_type": "approved",
        "rationale": "Strong financials",
        "new_stage": "clear_to_close",
        "ai_recommendation": "Approve",
        "ai_agreement": True,
        "override_rationale": None,
        "denial_reasons": None,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock compliance check audit event
    comp_event = MagicMock()
    comp_event.event_data = {"status": "PASS"}
    comp_result = MagicMock()
    comp_result.scalar_one_or_none.return_value = comp_event
    session.execute.return_value = comp_result

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Strong financials",
            "state": _state(),
        }
    )

    assert "Approved" in result
    assert "Clear To Close" in result
    assert "concurrence" in result


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_deny_success(mock_session_cls, mock_render):
    """uw_render_decision formats denial with reasons."""
    mock_render.return_value = {
        "id": 2,
        "decision_type": "denied",
        "rationale": "Insufficient income",
        "new_stage": "denied",
        "ai_recommendation": "Deny",
        "ai_agreement": True,
        "override_rationale": None,
        "denial_reasons": ["Insufficient income", "High DTI"],
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "deny",
            "rationale": "Insufficient income",
            "denial_reasons": ["Insufficient income", "High DTI"],
            "state": _state(),
        }
    )

    assert "Denied" in result
    assert "Insufficient income" in result
    assert "High DTI" in result


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_not_found(mock_session_cls, mock_render):
    """uw_render_decision returns not-found message."""
    mock_render.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    # No compliance check needed for deny
    result = await uw_render_decision.ainvoke(
        {
            "application_id": 999,
            "decision": "deny",
            "rationale": "test",
            "denial_reasons": ["test"],
            "state": _state(),
        }
    )

    assert "not found" in result


@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_compliance_gate_no_check(mock_session_cls):
    """uw_render_decision blocks approval when no compliance check exists."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    comp_result = MagicMock()
    comp_result.scalar_one_or_none.return_value = None
    session.execute.return_value = comp_result

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Good profile",
            "state": _state(),
        }
    )

    assert "compliance_check" in result.lower()


@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_compliance_gate_failed(mock_session_cls):
    """uw_render_decision blocks approval when compliance check failed."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    comp_event = MagicMock()
    comp_event.event_data = {"status": "FAIL", "failed_checks": ["ECOA"]}
    comp_result = MagicMock()
    comp_result.scalar_one_or_none.return_value = comp_event
    session.execute.return_value = comp_result

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Good profile",
            "state": _state(),
        }
    )

    assert "FAILED" in result
    assert "ECOA" in result


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_service_error(mock_session_cls, mock_render):
    """uw_render_decision returns service error message."""
    mock_render.return_value = {"error": "Wrong stage for this operation"}

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "deny",
            "rationale": "test",
            "denial_reasons": ["test"],
            "state": _state(),
        }
    )

    assert "Wrong stage" in result


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_override_info(mock_session_cls, mock_render):
    """uw_render_decision shows override information."""
    mock_render.return_value = {
        "id": 3,
        "decision_type": "approved",
        "rationale": "Compensating factors",
        "new_stage": "clear_to_close",
        "ai_recommendation": "Deny",
        "ai_agreement": False,
        "override_rationale": "Strong reserves",
        "denial_reasons": None,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    comp_event = MagicMock()
    comp_event.event_data = {"status": "PASS"}
    comp_result = MagicMock()
    comp_result.scalar_one_or_none.return_value = comp_event
    session.execute.return_value = comp_result

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Compensating factors",
            "override_rationale": "Strong reserves",
            "state": _state(),
        }
    )

    assert "override" in result.lower()
    assert "Strong reserves" in result


# ---------------------------------------------------------------------------
# uw_draft_adverse_action
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.write_audit_event", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_draft_adverse_action_success(mock_session_cls, mock_audit):
    """uw_draft_adverse_action generates notice text."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock get_application
    app = _mock_app()

    # Mock decision
    dec = _mock_decision(
        denial_reasons=["Low credit", "High DTI"],
        credit_score_used=580,
        credit_score_source="Equifax",
    )

    # Mock borrower
    ab = MagicMock()
    ab.borrower_id = 10

    borrower = MagicMock()
    borrower.first_name = "John"
    borrower.last_name = "Doe"

    # Set up execute side effects for multiple queries
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app

    dec_result = MagicMock()
    dec_result.scalar_one_or_none.return_value = dec

    ab_result = MagicMock()
    ab_result.scalar_one_or_none.return_value = ab

    b_result = MagicMock()
    b_result.scalar_one_or_none.return_value = borrower

    session.execute = AsyncMock(side_effect=[app_result, dec_result, ab_result, b_result])

    result = await uw_draft_adverse_action.ainvoke(
        {
            "application_id": 100,
            "decision_id": 1,
            "state": _state(),
        }
    )

    assert "ADVERSE ACTION NOTICE" in result
    assert "John Doe" in result
    assert "Low credit" in result
    assert "High DTI" in result
    assert "580" in result
    assert "Equifax" in result
    assert "DISCLAIMER" in result


@patch("src.agents.decision_tools.SessionLocal")
async def test_draft_adverse_action_not_found(mock_session_cls):
    """uw_draft_adverse_action returns error when app not found."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    result = await uw_draft_adverse_action.ainvoke(
        {
            "application_id": 999,
            "decision_id": 1,
            "state": _state(),
        }
    )

    assert "not found" in result


@patch("src.agents.decision_tools.SessionLocal")
async def test_draft_adverse_action_wrong_decision_type(mock_session_cls):
    """uw_draft_adverse_action rejects non-denial decisions."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app()
    dec = _mock_decision(decision_type="approved")

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app
    dec_result = MagicMock()
    dec_result.scalar_one_or_none.return_value = dec

    session.execute = AsyncMock(side_effect=[app_result, dec_result])

    result = await uw_draft_adverse_action.ainvoke(
        {
            "application_id": 100,
            "decision_id": 1,
            "state": _state(),
        }
    )

    assert "DENIED" in result


# ---------------------------------------------------------------------------
# uw_generate_le
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.write_audit_event", new_callable=AsyncMock)
@patch("src.agents.decision_tools.get_rate_lock_status", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_le_success(mock_session_cls, mock_rate_lock, mock_audit):
    """uw_generate_le generates LE text with loan details."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app()

    # Mock borrower lookup
    ab = MagicMock()
    ab.borrower_id = 10
    borrower = MagicMock()
    borrower.first_name = "Jane"
    borrower.last_name = "Smith"

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app
    ab_result = MagicMock()
    ab_result.scalar_one_or_none.return_value = ab
    b_result = MagicMock()
    b_result.scalar_one_or_none.return_value = borrower

    session.execute = AsyncMock(side_effect=[app_result, ab_result, b_result])
    mock_rate_lock.return_value = {"locked_rate": 6.5, "status": "active"}

    result = await uw_generate_le.ainvoke(
        {
            "application_id": 100,
            "state": _state(),
        }
    )

    assert "LOAN ESTIMATE" in result
    assert "Jane Smith" in result
    assert "$350,000.00" in result
    assert "6.500%" in result
    assert "123 Main St" in result
    assert "DISCLAIMER" in result
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "le_generated"


@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_le_not_found(mock_session_cls):
    """uw_generate_le returns error when app not found."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    result = await uw_generate_le.ainvoke(
        {
            "application_id": 999,
            "state": _state(),
        }
    )

    assert "not found" in result


# ---------------------------------------------------------------------------
# uw_generate_cd
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.write_audit_event", new_callable=AsyncMock)
@patch("src.agents.decision_tools.get_rate_lock_status", new_callable=AsyncMock)
@patch("src.agents.decision_tools.get_condition_summary", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_cd_success(mock_session_cls, mock_cond, mock_rate_lock, mock_audit):
    """uw_generate_cd generates CD text when conditions cleared."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app(stage="clear_to_close")
    mock_cond.return_value = {
        "total": 2,
        "counts": {
            "open": 0,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 1,
            "waived": 1,
        },
    }

    ab = MagicMock()
    ab.borrower_id = 10
    borrower = MagicMock()
    borrower.first_name = "Jane"
    borrower.last_name = "Smith"

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app
    ab_result = MagicMock()
    ab_result.scalar_one_or_none.return_value = ab
    b_result = MagicMock()
    b_result.scalar_one_or_none.return_value = borrower

    session.execute = AsyncMock(side_effect=[app_result, ab_result, b_result])
    mock_rate_lock.return_value = {"locked_rate": 6.5, "status": "active"}

    result = await uw_generate_cd.ainvoke(
        {
            "application_id": 100,
            "state": _state(),
        }
    )

    assert "CLOSING DISCLOSURE" in result
    assert "Jane Smith" in result
    assert "$350,000.00" in result
    assert "DISCLAIMER" in result
    mock_audit.assert_awaited_once()
    assert mock_audit.call_args.kwargs["event_type"] == "cd_generated"


@patch("src.agents.decision_tools.get_condition_summary", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_cd_outstanding_conditions(mock_session_cls, mock_cond):
    """uw_generate_cd blocks when conditions are outstanding."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app(stage="clear_to_close")
    mock_cond.return_value = {
        "total": 3,
        "counts": {
            "open": 1,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 1,
            "waived": 1,
        },
    }

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app
    session.execute.return_value = app_result

    result = await uw_generate_cd.ainvoke(
        {
            "application_id": 100,
            "state": _state(),
        }
    )

    assert "outstanding" in result.lower()
    assert "1 condition" in result


@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_cd_not_found(mock_session_cls):
    """uw_generate_cd returns error when app not found."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = None
    session.execute.return_value = app_result

    result = await uw_generate_cd.ainvoke(
        {
            "application_id": 999,
            "state": _state(),
        }
    )

    assert "not found" in result
