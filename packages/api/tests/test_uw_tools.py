# This project was developed with assistance from AI tools.
"""Unit tests for underwriter agent tools.

Focus: _user_context_from_state (underwriter scope), uw_queue_view
(read + urgency sorting), and uw_application_detail (multi-section output).
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db.enums import ApplicationStage, UserRole

from src.agents.underwriter_tools import (
    _user_context_from_state,
    uw_application_detail,
    uw_queue_view,
)

# ---------------------------------------------------------------------------
# _user_context_from_state
# ---------------------------------------------------------------------------


class TestUserContextFromState:
    """The helper that builds UserContext for all UW tools."""

    def test_builds_underwriter_scope(self):
        """underwriter role produces DataScope(full_pipeline=True)."""
        state = {
            "user_id": "uw-maria",
            "user_role": "underwriter",
            "user_email": "maria@summit-cap.com",
            "user_name": "Maria Chen",
        }
        ctx = _user_context_from_state(state)

        assert ctx.user_id == "uw-maria"
        assert ctx.role == UserRole.UNDERWRITER
        assert ctx.data_scope.full_pipeline is True
        assert ctx.data_scope.assigned_to is None
        assert ctx.data_scope.own_data_only is False


# ---------------------------------------------------------------------------
# uw_queue_view
# ---------------------------------------------------------------------------


class TestUwQueueView:
    """Verify queue listing with urgency sorting."""

    @pytest.mark.asyncio
    async def test_queue_returns_apps_with_urgency(self):
        """Mock 2 apps, verify formatting and urgency-based sorting."""
        mock_borrower1 = MagicMock()
        mock_borrower1.first_name = "Sarah"
        mock_borrower1.last_name = "Johnson"
        mock_ab1 = MagicMock()
        mock_ab1.borrower = mock_borrower1
        mock_ab1.is_primary = True

        mock_app1 = MagicMock()
        mock_app1.id = 1
        mock_app1.loan_amount = 350000
        mock_app1.property_address = "123 Oak St"
        mock_app1.assigned_to = "lo-james"
        mock_app1.application_borrowers = [mock_ab1]

        mock_borrower2 = MagicMock()
        mock_borrower2.first_name = "Tom"
        mock_borrower2.last_name = "Lee"
        mock_ab2 = MagicMock()
        mock_ab2.borrower = mock_borrower2
        mock_ab2.is_primary = True

        mock_app2 = MagicMock()
        mock_app2.id = 2
        mock_app2.loan_amount = 500000
        mock_app2.property_address = "456 Elm St"
        mock_app2.assigned_to = "lo-anna"
        mock_app2.application_borrowers = [mock_ab2]

        from src.schemas.urgency import UrgencyIndicator, UrgencyLevel

        urgency_map = {
            1: UrgencyIndicator(
                level=UrgencyLevel.NORMAL, factors=[], days_in_stage=2, expected_stage_days=5
            ),
            2: UrgencyIndicator(
                level=UrgencyLevel.HIGH,
                factors=["Rate lock expires in 5 days"],
                days_in_stage=4,
                expected_stage_days=5,
            ),
        }

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.list_applications",
                new_callable=AsyncMock,
                return_value=([mock_app1, mock_app2], 2),
            ),
            patch(
                "src.agents.underwriter_tools.compute_urgency",
                new_callable=AsyncMock,
                return_value=urgency_map,
            ),
            patch(
                "src.agents.underwriter_tools.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await uw_queue_view.ainvoke({"state": state})

        assert "Underwriting Queue (2 applications)" in result
        assert "Sarah Johnson" in result
        assert "Tom Lee" in result
        # HIGH urgency app should appear before NORMAL
        tom_pos = result.index("Tom Lee")
        sarah_pos = result.index("Sarah Johnson")
        assert tom_pos < sarah_pos

    @pytest.mark.asyncio
    async def test_queue_returns_empty(self):
        """No apps in underwriting returns empty message."""
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.list_applications",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.underwriter_tools.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await uw_queue_view.ainvoke({"state": state})

        assert "No applications in underwriting queue" in result

    @pytest.mark.asyncio
    async def test_queue_audits_access(self):
        """Verify audit event is written on queue view."""
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.list_applications",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.underwriter_tools.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await uw_queue_view.ainvoke({"state": state})

        mock_audit.assert_awaited_once()
        audit_call = mock_audit.call_args
        assert audit_call.kwargs["event_type"] == "data_access"
        assert audit_call.kwargs["event_data"]["action"] == "underwriter_queue_view"


# ---------------------------------------------------------------------------
# uw_application_detail
# ---------------------------------------------------------------------------


class TestUwApplicationDetail:
    """Verify multi-section application detail output."""

    @pytest.mark.asyncio
    async def test_detail_returns_full_info(self):
        """Mock app, financials, docs, conditions -- verify all sections present."""
        mock_borrower = MagicMock()
        mock_borrower.first_name = "Sarah"
        mock_borrower.last_name = "Johnson"
        mock_borrower.email = "sarah@test.com"
        mock_borrower.employment_status = MagicMock(value="w2_employee")

        mock_ab = MagicMock()
        mock_ab.borrower = mock_borrower
        mock_ab.is_primary = True

        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.loan_type = MagicMock(value="conventional_30")
        mock_app.loan_amount = 350000
        mock_app.property_value = 450000
        mock_app.property_address = "123 Oak St"
        mock_app.application_borrowers = [mock_ab]

        mock_fin = MagicMock()
        mock_fin.gross_monthly_income = 8000
        mock_fin.monthly_debts = 2500
        mock_fin.total_assets = 120000
        mock_fin.credit_score = 720

        mock_doc = MagicMock()
        mock_doc.id = 10
        mock_doc.doc_type = MagicMock(value="w2_form")
        mock_doc.status = MagicMock(value="processing_complete")
        mock_doc.quality_flags = None

        mock_conditions = [
            {
                "id": 1,
                "description": "Verify employment",
                "severity": "prior_to_approval",
                "status": "open",
            }
        ]

        mock_rate_lock = {
            "status": "active",
            "locked_rate": 6.75,
            "expiration_date": "2025-04-15",
            "days_remaining": 10,
            "is_urgent": False,
        }

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.underwriter_tools.list_documents",
                new_callable=AsyncMock,
                return_value=([mock_doc], 1),
            ),
            patch(
                "src.agents.underwriter_tools.get_conditions",
                new_callable=AsyncMock,
                return_value=mock_conditions,
            ),
            patch(
                "src.agents.underwriter_tools.get_rate_lock_status",
                new_callable=AsyncMock,
                return_value=mock_rate_lock,
            ),
            patch(
                "src.agents.underwriter_tools.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            # Mock the financials query
            mock_fin_result = MagicMock()
            mock_fin_result.scalars.return_value.all.return_value = [mock_fin]
            mock_session.execute = AsyncMock(return_value=mock_fin_result)
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await uw_application_detail.ainvoke({"application_id": 101, "state": state})

        assert "Application #101" in result
        assert "BORROWER PROFILE:" in result
        assert "Sarah Johnson" in result
        assert "W2 Employee" in result
        assert "FINANCIAL SUMMARY:" in result
        assert "$8,000.00" in result
        assert "DTI ratio:" in result
        assert "LOAN DETAILS:" in result
        assert "LTV ratio:" in result
        assert "DOCUMENTS (1):" in result
        assert "w2_form" in result
        assert "CONDITIONS (1):" in result
        assert "Verify employment" in result
        assert "RATE LOCK:" in result
        assert "6.750%" in result

    @pytest.mark.asyncio
    async def test_detail_not_found(self):
        """get_application returns None => error message."""
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.get_application",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await uw_application_detail.ainvoke({"application_id": 999, "state": state})

        assert "not found" in result.lower()

    @pytest.mark.asyncio
    async def test_detail_audits_view(self):
        """Verify audit event is written on detail view."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.loan_type = None
        mock_app.loan_amount = None
        mock_app.property_value = None
        mock_app.property_address = None
        mock_app.application_borrowers = []

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.underwriter_tools.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.underwriter_tools.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.underwriter_tools.get_conditions",
                new_callable=AsyncMock,
                return_value=[],
            ),
            patch(
                "src.agents.underwriter_tools.get_rate_lock_status",
                new_callable=AsyncMock,
                return_value={"status": "none"},
            ),
            patch(
                "src.agents.underwriter_tools.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch("src.agents.underwriter_tools.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_fin_result = MagicMock()
            mock_fin_result.scalars.return_value.all.return_value = []
            mock_session.execute = AsyncMock(return_value=mock_fin_result)
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await uw_application_detail.ainvoke({"application_id": 101, "state": state})

        mock_audit.assert_awaited_once()
        audit_call = mock_audit.call_args
        assert audit_call.kwargs["event_type"] == "data_access"
        assert audit_call.kwargs["event_data"]["action"] == "underwriter_detail_view"
