# This project was developed with assistance from AI tools.
"""Tests for decision agent tools."""

from unittest.mock import AsyncMock, MagicMock, patch

from src.agents.decision_tools import (
    uw_draft_adverse_action,
    uw_generate_cd,
    uw_generate_le,
    uw_render_decision,
)
from tests.factories import make_mock_app, make_mock_decision

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(user_id="uw-maria", role="underwriter"):
    return {"user_id": user_id, "user_role": role}


_mock_app = make_mock_app
_mock_decision = make_mock_decision


# ---------------------------------------------------------------------------
# uw_render_decision -- Phase 1 (propose, confirmed=false)
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.propose_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_propose_approve(mock_session_cls, mock_propose):
    """Phase 1: uw_render_decision returns a proposal without persisting."""
    mock_propose.return_value = {
        "proposal": True,
        "application_id": 100,
        "decision_type": "approved",
        "new_stage": "clear_to_close",
        "current_stage": "underwriting",
        "rationale": "Strong financials",
        "ai_recommendation": "Approve",
        "ai_agreement": True,
        "denial_reasons": None,
        "outstanding_conditions": 0,
        "override_rationale": None,
    }

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock compliance gate pass
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

    assert "PROPOSED DECISION" in result
    assert "Approved" in result
    assert "NOT been recorded" in result
    assert "confirm" in result.lower()
    mock_propose.assert_awaited_once()


@patch("src.agents.decision_tools.propose_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_propose_deny(mock_session_cls, mock_propose):
    """Phase 1: denial proposal shows reasons."""
    mock_propose.return_value = {
        "proposal": True,
        "application_id": 100,
        "decision_type": "denied",
        "new_stage": "denied",
        "current_stage": "underwriting",
        "rationale": "Insufficient income",
        "ai_recommendation": "Deny",
        "ai_agreement": True,
        "denial_reasons": ["Insufficient income", "High DTI"],
        "outstanding_conditions": 0,
        "override_rationale": None,
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

    assert "PROPOSED DECISION" in result
    assert "Insufficient income" in result
    assert "High DTI" in result


# ---------------------------------------------------------------------------
# uw_render_decision -- Phase 2 (confirmed=true)
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_confirmed_approve(mock_session_cls, mock_render):
    """Phase 2: confirmed=true executes the decision."""
    mock_render.return_value = {
        "id": 1,
        "application_id": 100,
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

    comp_event = MagicMock()
    comp_event.event_data = {"status": "PASS"}
    comp_result = MagicMock()
    comp_result.scalar_one_or_none.return_value = comp_event
    session.execute.return_value = comp_result

    state = _state()
    state["decision_proposals"] = {
        "test-proposal-1": {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Strong financials",
        },
    }

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "approve",
            "rationale": "Strong financials",
            "confirmed": True,
            "proposal_id": "test-proposal-1",
            "state": state,
        }
    )

    assert "Decision rendered" in result
    assert "Decision ID: 1" in result
    assert "Approved" in result
    assert "Clear To Close" in result
    mock_render.assert_awaited_once()


@patch("src.agents.decision_tools.render_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_confirmed_deny(mock_session_cls, mock_render):
    """Phase 2: confirmed denial with reasons."""
    mock_render.return_value = {
        "id": 2,
        "application_id": 100,
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

    state = _state()
    state["decision_proposals"] = {
        "test-proposal-2": {
            "application_id": 100,
            "decision": "deny",
            "rationale": "Insufficient income",
        },
    }

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "deny",
            "rationale": "Insufficient income",
            "denial_reasons": ["Insufficient income", "High DTI"],
            "confirmed": True,
            "proposal_id": "test-proposal-2",
            "state": state,
        }
    )

    assert "Decision rendered" in result
    assert "Denied" in result


# ---------------------------------------------------------------------------
# uw_render_decision -- edge cases (both phases)
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.propose_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_not_found(mock_session_cls, mock_propose):
    """uw_render_decision returns not-found message."""
    mock_propose.return_value = None

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

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
async def test_render_decision_confirmed_service_error(mock_session_cls, mock_render):
    """Phase 2: returns service error message."""
    mock_render.return_value = {"error": "Wrong stage for this operation"}

    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    state = _state()
    state["decision_proposals"] = {
        "test-proposal-3": {
            "application_id": 100,
            "decision": "deny",
            "rationale": "test",
        },
    }

    result = await uw_render_decision.ainvoke(
        {
            "application_id": 100,
            "decision": "deny",
            "rationale": "test",
            "denial_reasons": ["test"],
            "confirmed": True,
            "proposal_id": "test-proposal-3",
            "state": state,
        }
    )

    assert "Wrong stage" in result


@patch("src.agents.decision_tools.propose_decision", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_render_decision_propose_override_warning(mock_session_cls, mock_propose):
    """Phase 1: proposal shows override warning when AI disagrees."""
    mock_propose.return_value = {
        "proposal": True,
        "application_id": 100,
        "decision_type": "approved",
        "new_stage": "clear_to_close",
        "current_stage": "underwriting",
        "rationale": "Compensating factors",
        "ai_recommendation": "Deny",
        "ai_agreement": False,
        "denial_reasons": None,
        "outstanding_conditions": 0,
        "override_rationale": "Strong reserves",
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

    assert "OVERRIDE" in result
    assert "Strong reserves" in result
    assert "NOT been recorded" in result


# ---------------------------------------------------------------------------
# uw_draft_adverse_action
# ---------------------------------------------------------------------------


@patch("src.agents.decision_tools.write_audit_event", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_draft_adverse_action_success(mock_session_cls, mock_audit):
    """uw_draft_adverse_action generates notice text with explicit decision_id."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    # Mock get_application
    app = _mock_app()

    # Mock decision
    dec = _mock_decision(
        decision_type="denied",
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


@patch("src.agents.decision_tools.write_audit_event", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_draft_adverse_action_auto_find(mock_session_cls, mock_audit):
    """uw_draft_adverse_action auto-finds latest DENIED decision when no ID given."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app()
    dec = _mock_decision(
        id=42,
        decision_type="denied",
        denial_reasons=["Insufficient income"],
        credit_score_used=620,
        credit_score_source="TransUnion",
    )

    ab = MagicMock()
    ab.borrower_id = 10
    borrower = MagicMock()
    borrower.first_name = "Alice"
    borrower.last_name = "Chen"

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
            "state": _state(),
        }
    )

    assert "ADVERSE ACTION NOTICE" in result
    assert "Alice Chen" in result
    assert "Insufficient income" in result
    assert "620" in result


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
async def test_draft_adverse_action_no_denied_decision(mock_session_cls):
    """uw_draft_adverse_action returns error when no DENIED decision exists."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app()
    app_result = MagicMock()
    app_result.unique.return_value.scalar_one_or_none.return_value = app
    dec_result = MagicMock()
    dec_result.scalar_one_or_none.return_value = None

    session.execute = AsyncMock(side_effect=[app_result, dec_result])

    result = await uw_draft_adverse_action.ainvoke(
        {
            "application_id": 100,
            "state": _state(),
        }
    )

    assert "No DENIED decision" in result


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
@patch("src.agents.disclosure_tools.get_rate_lock_status", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_le_success(
    mock_session_cls, mock_rate_lock_disclosure, mock_rate_lock, mock_audit
):
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
    mock_rate_lock_disclosure.return_value = {"locked_rate": 6.5, "status": "active"}

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
@patch("src.agents.disclosure_tools.get_rate_lock_status", new_callable=AsyncMock)
@patch("src.agents.decision_tools.get_outstanding_count", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_cd_success(
    mock_session_cls, mock_cond, mock_rate_lock_disclosure, mock_rate_lock, mock_audit
):
    """uw_generate_cd generates CD text when conditions cleared."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app(stage="clear_to_close")
    mock_cond.return_value = 0  # All conditions cleared or waived

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
    mock_rate_lock_disclosure.return_value = {"locked_rate": 6.5, "status": "active"}

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


@patch("src.agents.decision_tools.get_outstanding_count", new_callable=AsyncMock)
@patch("src.agents.decision_tools.SessionLocal")
async def test_generate_cd_outstanding_conditions(mock_session_cls, mock_cond):
    """uw_generate_cd blocks when conditions are outstanding."""
    session = AsyncMock()
    mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=session)
    mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

    app = _mock_app(stage="clear_to_close")
    mock_cond.return_value = 1  # 1 outstanding condition

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
