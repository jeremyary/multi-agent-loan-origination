# This project was developed with assistance from AI tools.
"""Tests for decision service."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.schemas.decision import DecisionItem, DecisionListResponse, DecisionResponse
from src.services.decision import (
    _ai_category,
    _decision_category,
    _get_ai_recommendation,
    get_decisions,
    get_latest_decision,
    render_decision,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_app(stage="underwriting", id=100):
    """Create a mock application with the given stage."""
    from db.enums import ApplicationStage

    app = MagicMock()
    app.stage = ApplicationStage(stage)
    app.id = id
    app.loan_amount = None
    app.property_value = None
    app.loan_type = None
    app.property_address = None
    return app


def _uw_user():
    """Create a mock underwriter UserContext."""
    user = MagicMock()
    user.user_id = "uw-maria"
    user.role = MagicMock()
    user.role.value = "underwriter"
    user.data_scope = MagicMock()
    return user


def _mock_decision(
    id=1,
    application_id=100,
    decision_type="approved",
    rationale="Strong profile",
    ai_recommendation=None,
    ai_agreement=None,
    denial_reasons=None,
    credit_score_used=None,
    credit_score_source=None,
    contributing_factors=None,
):
    """Create a mock Decision ORM object."""
    from db.enums import DecisionType

    d = MagicMock()
    d.id = id
    d.application_id = application_id
    d.decision_type = DecisionType(decision_type)
    d.rationale = rationale
    d.ai_recommendation = ai_recommendation
    d.ai_agreement = ai_agreement
    d.override_rationale = None
    d.denial_reasons = json.dumps(denial_reasons) if denial_reasons else None
    d.credit_score_used = credit_score_used
    d.credit_score_source = credit_score_source
    d.contributing_factors = contributing_factors
    d.decided_by = "uw-maria"
    d.created_at = MagicMock()
    d.created_at.isoformat.return_value = "2026-02-27T12:00:00+00:00"
    return d


# ---------------------------------------------------------------------------
# Schema tests
# ---------------------------------------------------------------------------


def test_decision_item_schema():
    item = DecisionItem(
        id=1,
        application_id=100,
        decision_type="approved",
        rationale="Strong financials",
    )
    assert item.id == 1
    assert item.decision_type == "approved"


def test_decision_response_schema():
    resp = DecisionResponse(
        data=DecisionItem(
            id=1,
            application_id=100,
            decision_type="denied",
            denial_reasons=["Low credit", "High DTI"],
        )
    )
    assert resp.data.denial_reasons == ["Low credit", "High DTI"]


def test_decision_list_response_schema():
    from src.schemas import Pagination

    resp = DecisionListResponse(
        data=[
            DecisionItem(id=1, application_id=100, decision_type="approved"),
            DecisionItem(id=2, application_id=100, decision_type="denied"),
        ],
        pagination=Pagination(total=2, offset=0, limit=20, has_more=False),
    )
    assert resp.pagination.total == 2
    assert len(resp.data) == 2


# ---------------------------------------------------------------------------
# Pure function tests
# ---------------------------------------------------------------------------


def test_decision_category_mapping():
    from db.enums import DecisionType

    assert _decision_category(DecisionType.APPROVED) == "approve"
    assert _decision_category(DecisionType.CONDITIONAL_APPROVAL) == "approve"
    assert _decision_category(DecisionType.DENIED) == "deny"
    assert _decision_category(DecisionType.SUSPENDED) == "suspend"


def test_ai_category_mapping():
    assert _ai_category("Approve") == "approve"
    assert _ai_category("Approve with Conditions") == "approve"
    assert _ai_category("Deny") == "deny"
    assert _ai_category("Suspend") == "suspend"
    assert _ai_category(None) is None
    assert _ai_category("something random") is None


# ---------------------------------------------------------------------------
# _get_ai_recommendation
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_ai_recommendation_finds_recommendation():
    session = AsyncMock()

    event = MagicMock()
    event.event_data = {
        "tool": "uw_preliminary_recommendation",
        "recommendation": "Approve",
    }

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [event]
    session.execute.return_value = mock_result

    text, category = await _get_ai_recommendation(session, 100)
    assert text == "Approve"
    assert category == "Approve"


@pytest.mark.asyncio
async def test_get_ai_recommendation_returns_none_when_no_recommendation():
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    text, category = await _get_ai_recommendation(session, 100)
    assert text is None
    assert category is None


# ---------------------------------------------------------------------------
# render_decision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_out_of_scope(mock_get_app, mock_ai, mock_cond, mock_audit):
    """render_decision returns None when application not found."""
    mock_get_app.return_value = None
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 999, "approve", "Good profile")
    assert result is None


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_wrong_stage(mock_get_app, mock_ai, mock_cond, mock_audit):
    """render_decision returns error when app is in wrong stage."""
    mock_get_app.return_value = _mock_app(stage="application")
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 100, "approve", "Good profile")
    assert result is not None
    assert "error" in result
    assert "underwriting" in result["error"].lower()


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_approve_no_conditions(mock_get_app, mock_ai, mock_cond, mock_audit):
    """Approve from UNDERWRITING with no conditions -> APPROVED + CLEAR_TO_CLOSE."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Approve", "Approve")
    mock_cond.return_value = {
        "total": 0,
        "counts": {
            "open": 0,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 0,
            "waived": 0,
        },
    }
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 1
        from db.enums import DecisionType

        obj.decision_type = DecisionType.APPROVED
        obj.rationale = "Strong financials"
        obj.ai_recommendation = "Approve"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(session, _uw_user(), 100, "approve", "Strong financials")
    assert result is not None
    assert "error" not in result
    assert result["decision_type"] == "approved"
    assert result["new_stage"] == "clear_to_close"
    assert result["ai_agreement"] is True


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_approve_with_conditions(
    mock_get_app, mock_ai, mock_cond, mock_audit
):
    """Approve from UNDERWRITING with outstanding conditions -> CONDITIONAL_APPROVAL."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Approve with Conditions", "Approve with Conditions")
    mock_cond.return_value = {
        "total": 2,
        "counts": {
            "open": 2,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 0,
            "waived": 0,
        },
    }
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 2
        from db.enums import DecisionType

        obj.decision_type = DecisionType.CONDITIONAL_APPROVAL
        obj.rationale = "Subject to conditions"
        obj.ai_recommendation = "Approve with Conditions"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(session, _uw_user(), 100, "approve", "Subject to conditions")
    assert result is not None
    assert result["decision_type"] == "conditional_approval"
    assert result["new_stage"] == "conditional_approval"


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_approve_from_conditional_all_cleared(
    mock_get_app, mock_ai, mock_cond, mock_audit
):
    """Approve from CONDITIONAL_APPROVAL (all cleared) -> APPROVED + CLEAR_TO_CLOSE."""
    app = _mock_app(stage="conditional_approval")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Approve", "Approve")
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
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 3
        from db.enums import DecisionType

        obj.decision_type = DecisionType.APPROVED
        obj.rationale = "All conditions met"
        obj.ai_recommendation = "Approve"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(session, _uw_user(), 100, "approve", "All conditions met")
    assert result is not None
    assert result["decision_type"] == "approved"
    assert result["new_stage"] == "clear_to_close"


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_approve_from_conditional_outstanding(
    mock_get_app, mock_ai, mock_cond, mock_audit
):
    """Approve from CONDITIONAL_APPROVAL with outstanding conditions -> error."""
    app = _mock_app(stage="conditional_approval")
    mock_get_app.return_value = app
    mock_ai.return_value = (None, None)
    mock_cond.return_value = {
        "total": 2,
        "counts": {
            "open": 1,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 1,
            "waived": 0,
        },
    }
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 100, "approve", "Trying to approve")
    assert result is not None
    assert "error" in result
    assert "outstanding conditions" in result["error"].lower()


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_deny(mock_get_app, mock_ai, mock_audit):
    """Deny from UNDERWRITING -> DENIED + stage DENIED."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Deny", "Deny")
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 4
        from db.enums import DecisionType

        obj.decision_type = DecisionType.DENIED
        obj.rationale = "Insufficient income"
        obj.ai_recommendation = "Deny"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = json.dumps(["Insufficient income", "High DTI"])
        obj.credit_score_used = 620
        obj.credit_score_source = "Equifax"
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(
        session,
        _uw_user(),
        100,
        "deny",
        "Insufficient income",
        denial_reasons=["Insufficient income", "High DTI"],
        credit_score_used=620,
        credit_score_source="Equifax",
    )
    assert result is not None
    assert "error" not in result
    assert result["decision_type"] == "denied"
    assert result["new_stage"] == "denied"
    assert result["denial_reasons"] == ["Insufficient income", "High DTI"]


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_deny_without_reasons(mock_get_app, mock_ai, mock_audit):
    """Deny without denial_reasons -> error."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = (None, None)
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 100, "deny", "Bad profile")
    assert result is not None
    assert "error" in result
    assert "denial_reason" in result["error"].lower()


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_deny_from_conditional(mock_get_app, mock_ai, mock_audit):
    """Deny from CONDITIONAL_APPROVAL -> DENIED."""
    app = _mock_app(stage="conditional_approval")
    mock_get_app.return_value = app
    mock_ai.return_value = (None, None)
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 5
        from db.enums import DecisionType

        obj.decision_type = DecisionType.DENIED
        obj.rationale = "Failed to clear conditions"
        obj.ai_recommendation = None
        obj.ai_agreement = None
        obj.override_rationale = None
        obj.denial_reasons = json.dumps(["Failed to clear conditions"])
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(
        session,
        _uw_user(),
        100,
        "deny",
        "Failed to clear conditions",
        denial_reasons=["Failed to clear conditions"],
    )
    assert result is not None
    assert result["decision_type"] == "denied"
    assert result["new_stage"] == "denied"


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_suspend(mock_get_app, mock_ai, mock_audit):
    """Suspend from UNDERWRITING -> SUSPENDED + no stage change."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Suspend", "Suspend")
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 6
        from db.enums import DecisionType

        obj.decision_type = DecisionType.SUSPENDED
        obj.rationale = "Missing documents"
        obj.ai_recommendation = "Suspend"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(session, _uw_user(), 100, "suspend", "Missing documents")
    assert result is not None
    assert "error" not in result
    assert result["decision_type"] == "suspended"
    assert result["new_stage"] is None


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_suspend_from_conditional_error(mock_get_app, mock_ai, mock_audit):
    """Suspend from CONDITIONAL_APPROVAL -> error."""
    app = _mock_app(stage="conditional_approval")
    mock_get_app.return_value = app
    mock_ai.return_value = (None, None)
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 100, "suspend", "Need more info")
    assert result is not None
    assert "error" in result
    assert "UNDERWRITING" in result["error"]


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_ai_agreement(mock_get_app, mock_ai, mock_cond, mock_audit):
    """AI concurrence detected when UW and AI both say approve."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Approve", "Approve")
    mock_cond.return_value = {
        "total": 0,
        "counts": {
            "open": 0,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 0,
            "waived": 0,
        },
    }
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 7
        from db.enums import DecisionType

        obj.decision_type = DecisionType.APPROVED
        obj.rationale = "Good profile"
        obj.ai_recommendation = "Approve"
        obj.ai_agreement = True
        obj.override_rationale = None
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(session, _uw_user(), 100, "approve", "Good profile")
    assert result is not None
    assert result["ai_agreement"] is True
    # No override audit event should be written -- check audit calls
    decision_audit_calls = [
        c for c in mock_audit.call_args_list if c.kwargs.get("event_type") == "override"
    ]
    assert len(decision_audit_calls) == 0


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision.get_condition_summary", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_ai_override(mock_get_app, mock_ai, mock_cond, mock_audit):
    """AI override detected when UW approves but AI said deny."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = ("Deny", "Deny")
    mock_cond.return_value = {
        "total": 0,
        "counts": {
            "open": 0,
            "responded": 0,
            "under_review": 0,
            "escalated": 0,
            "cleared": 0,
            "waived": 0,
        },
    }
    session = AsyncMock()

    async def fake_refresh(obj):
        obj.id = 8
        from db.enums import DecisionType

        obj.decision_type = DecisionType.APPROVED
        obj.rationale = "Compensating factors present"
        obj.ai_recommendation = "Deny"
        obj.ai_agreement = False
        obj.override_rationale = "Strong reserves offset risk"
        obj.denial_reasons = None
        obj.credit_score_used = None
        obj.credit_score_source = None
        obj.contributing_factors = None
        obj.decided_by = "uw-maria"
        obj.application_id = 100

    session.refresh = fake_refresh

    result = await render_decision(
        session,
        _uw_user(),
        100,
        "approve",
        "Compensating factors present",
        override_rationale="Strong reserves offset risk",
    )
    assert result is not None
    assert result["ai_agreement"] is False

    # Override audit event should be written
    override_calls = [
        c for c in mock_audit.call_args_list if c.kwargs.get("event_type") == "override"
    ]
    assert len(override_calls) == 1
    override_data = override_calls[0].kwargs["event_data"]
    assert override_data["high_risk"] is True


@pytest.mark.asyncio
@patch("src.services.decision.write_audit_event", new_callable=AsyncMock)
@patch("src.services.decision._get_ai_recommendation", new_callable=AsyncMock)
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_render_decision_invalid_decision_type(mock_get_app, mock_ai, mock_audit):
    """Invalid decision string -> error."""
    app = _mock_app(stage="underwriting")
    mock_get_app.return_value = app
    mock_ai.return_value = (None, None)
    session = AsyncMock()

    result = await render_decision(session, _uw_user(), 100, "maybe", "Unsure")
    assert result is not None
    assert "error" in result
    assert "Invalid decision" in result["error"]


# ---------------------------------------------------------------------------
# get_decisions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_decisions_out_of_scope(mock_get_app):
    """get_decisions returns None when application not found."""
    mock_get_app.return_value = None
    session = AsyncMock()

    result = await get_decisions(session, _uw_user(), 999)
    assert result is None


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_decisions_empty(mock_get_app):
    """get_decisions returns empty list when no decisions."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    session.execute.return_value = mock_result

    result = await get_decisions(session, _uw_user(), 100)
    assert result == []


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_decisions_returns_ordered_list(mock_get_app):
    """get_decisions returns decisions ordered by created_at."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    d1 = _mock_decision(id=1, decision_type="conditional_approval")
    d2 = _mock_decision(id=2, decision_type="approved")

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [d1, d2]
    session.execute.return_value = mock_result

    result = await get_decisions(session, _uw_user(), 100)
    assert len(result) == 2
    assert result[0]["id"] == 1
    assert result[0]["decision_type"] == "conditional_approval"
    assert result[1]["id"] == 2
    assert result[1]["decision_type"] == "approved"


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_decisions_includes_adverse_action_fields(mock_get_app):
    """get_decisions includes credit score and denial reasons."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    d = _mock_decision(
        id=3,
        decision_type="denied",
        denial_reasons=["Low credit score"],
        credit_score_used=580,
        credit_score_source="TransUnion",
    )

    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [d]
    session.execute.return_value = mock_result

    result = await get_decisions(session, _uw_user(), 100)
    assert len(result) == 1
    assert result[0]["denial_reasons"] == ["Low credit score"]
    assert result[0]["credit_score_used"] == 580
    assert result[0]["credit_score_source"] == "TransUnion"


# ---------------------------------------------------------------------------
# get_latest_decision
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_latest_decision_out_of_scope(mock_get_app):
    """get_latest_decision returns None when application not found."""
    mock_get_app.return_value = None
    session = AsyncMock()

    result = await get_latest_decision(session, _uw_user(), 999)
    assert result is None


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_latest_decision_returns_most_recent(mock_get_app):
    """get_latest_decision returns the most recent decision."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    d = _mock_decision(id=5, decision_type="approved")
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = d
    session.execute.return_value = mock_result

    result = await get_latest_decision(session, _uw_user(), 100)
    assert result is not None
    assert result["id"] == 5
    assert result["decision_type"] == "approved"


@pytest.mark.asyncio
@patch("src.services.decision.get_application", new_callable=AsyncMock)
async def test_get_latest_decision_no_decisions(mock_get_app):
    """get_latest_decision returns indicator when no decisions exist."""
    mock_get_app.return_value = _mock_app()
    session = AsyncMock()

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result

    result = await get_latest_decision(session, _uw_user(), 100)
    assert result is not None
    assert result.get("no_decisions") is True
