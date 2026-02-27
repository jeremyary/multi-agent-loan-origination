# This project was developed with assistance from AI tools.
"""Unit tests for loan officer agent tools.

Focus: _user_context_from_state (affects all tools), one representative
read tool, and the two write tools with real logic (mark resubmission,
submit to underwriting).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db.enums import ApplicationStage, UserRole

from src.agents.loan_officer_tools import (
    _user_context_from_state,
    lo_application_detail,
    lo_mark_resubmission,
    lo_submit_to_underwriting,
)

# ---------------------------------------------------------------------------
# _user_context_from_state
# ---------------------------------------------------------------------------


class TestUserContextFromState:
    """The helper that builds UserContext for all LO tools."""

    def test_builds_lo_scope(self):
        """loan_officer role produces DataScope(assigned_to=user_id)."""
        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
            "user_email": "james@summit-cap.com",
            "user_name": "James Torres",
        }
        ctx = _user_context_from_state(state)

        assert ctx.user_id == "lo-james"
        assert ctx.role == UserRole.LOAN_OFFICER
        assert ctx.data_scope.assigned_to == "lo-james"
        assert ctx.data_scope.own_data_only is False
        assert ctx.data_scope.full_pipeline is False


# ---------------------------------------------------------------------------
# Representative read tool
# ---------------------------------------------------------------------------


class TestLoApplicationDetail:
    """Verify the read pattern: calls services and produces output."""

    @pytest.mark.asyncio
    async def test_calls_services_and_formats(self):
        """lo_application_detail calls get_application + get_application_status."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.APPLICATION
        mock_app.loan_type = MagicMock(value="conventional_30")
        mock_app.property_address = "123 Oak St"
        mock_app.loan_amount = 350000
        mock_app.property_value = 450000
        mock_app.application_borrowers = []

        mock_status = MagicMock()
        mock_status.provided_doc_count = 3
        mock_status.required_doc_count = 4
        mock_status.is_document_complete = False
        mock_status.open_condition_count = 0
        mock_status.pending_actions = []

        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
        }

        with (
            patch(
                "src.agents.loan_officer_tools.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ) as mock_get_app,
            patch(
                "src.agents.loan_officer_tools.get_application_status",
                new_callable=AsyncMock,
                return_value=mock_status,
            ) as mock_get_status,
            patch(
                "src.agents.loan_officer_tools.SessionLocal",
            ) as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await lo_application_detail.ainvoke({"application_id": 101, "state": state})

        assert "Application #101" in result
        assert "Application" in result  # stage
        assert "3/4" in result  # doc counts
        mock_get_app.assert_awaited_once()
        mock_get_status.assert_awaited_once()


# ---------------------------------------------------------------------------
# lo_mark_resubmission (write tool)
# ---------------------------------------------------------------------------


class TestLoMarkResubmission:
    """Write tool: update_document_status + write_audit_event."""

    @pytest.mark.asyncio
    async def test_writes_status_and_audit(self):
        """Marks doc for resubmission and writes audit event."""
        mock_doc = MagicMock()
        mock_doc.id = 10

        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
        }

        with (
            patch(
                "src.agents.loan_officer_tools.update_document_status",
                new_callable=AsyncMock,
                return_value=mock_doc,
            ) as mock_update,
            patch(
                "src.agents.loan_officer_tools.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch(
                "src.agents.loan_officer_tools.SessionLocal",
            ) as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await lo_mark_resubmission.ainvoke(
                {
                    "application_id": 101,
                    "document_id": 10,
                    "reason": "Illegible scan",
                    "state": state,
                }
            )

        assert "flagged for resubmission" in result
        mock_update.assert_awaited_once()
        mock_audit.assert_awaited_once()
        # Verify audit event type
        audit_call = mock_audit.call_args
        assert audit_call.kwargs["event_type"] == "document_flagged_for_resubmission"


# ---------------------------------------------------------------------------
# lo_submit_to_underwriting (write tool)
# ---------------------------------------------------------------------------


class TestLoSubmitToUnderwriting:
    """The most important test -- double transition + dual audit."""

    @pytest.mark.asyncio
    async def test_happy_path_dual_transition(self):
        """Both transitions happen in order with audit events."""
        mock_app_processing = MagicMock()
        mock_app_processing.stage = ApplicationStage.PROCESSING

        mock_app_underwriting = MagicMock()
        mock_app_underwriting.stage = ApplicationStage.UNDERWRITING

        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
        }

        with (
            patch(
                "src.agents.loan_officer_tools.check_underwriting_readiness",
                new_callable=AsyncMock,
                return_value={"is_ready": True, "blockers": []},
            ),
            patch(
                "src.agents.loan_officer_tools.transition_stage",
                new_callable=AsyncMock,
                side_effect=[mock_app_processing, mock_app_underwriting],
            ) as mock_transition,
            patch(
                "src.agents.loan_officer_tools.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch(
                "src.agents.loan_officer_tools.SessionLocal",
            ) as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await lo_submit_to_underwriting.ainvoke(
                {"application_id": 101, "state": state}
            )

        assert "submitted to underwriting" in result
        assert mock_transition.await_count == 2

        # Verify transition order
        calls = mock_transition.call_args_list
        assert calls[0].args[3] == ApplicationStage.PROCESSING
        assert calls[1].args[3] == ApplicationStage.UNDERWRITING

        # Two audit events
        assert mock_audit.await_count == 2

    @pytest.mark.asyncio
    async def test_blocked_when_not_ready(self):
        """Readiness gate blocks submission and returns blockers."""
        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
        }

        with (
            patch(
                "src.agents.loan_officer_tools.check_underwriting_readiness",
                new_callable=AsyncMock,
                return_value={
                    "is_ready": False,
                    "blockers": ["Missing required documents: W-2 Form"],
                },
            ),
            patch(
                "src.agents.loan_officer_tools.transition_stage",
                new_callable=AsyncMock,
            ) as mock_transition,
            patch(
                "src.agents.loan_officer_tools.SessionLocal",
            ) as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await lo_submit_to_underwriting.ainvoke(
                {"application_id": 101, "state": state}
            )

        assert "not ready" in result
        assert "W-2 Form" in result
        mock_transition.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_app_not_found(self):
        """Returns error message (not exception) when app is out of scope."""
        state = {
            "user_id": "lo-james",
            "user_role": "loan_officer",
        }

        with (
            patch(
                "src.agents.loan_officer_tools.check_underwriting_readiness",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch(
                "src.agents.loan_officer_tools.SessionLocal",
            ) as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await lo_submit_to_underwriting.ainvoke(
                {"application_id": 999, "state": state}
            )

        assert "not found" in result.lower()
