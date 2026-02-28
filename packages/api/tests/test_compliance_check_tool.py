# This project was developed with assistance from AI tools.
"""Unit tests for the compliance_check LangGraph tool.

Mocked DB pattern matching test_uw_tools.py -- verifies tool behavior
for each regulation type, stage guard, not-found, and audit logging.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from db.enums import ApplicationStage, DocumentType

from src.agents.compliance_check_tool import compliance_check


def _mock_session_with_fins(financials_rows, has_demographics=True):
    """Create a mock session that returns given financials and demographics from execute().

    Args:
        financials_rows: List of mock financial rows to return.
        has_demographics: If True, demographic query returns a record; if False, returns None.
    """
    mock_session = AsyncMock()

    # First execute() call: financials query
    mock_fin_result = MagicMock()
    mock_fin_result.scalars.return_value.all.return_value = financials_rows

    # Second execute() call: demographics query
    mock_demog_result = MagicMock()
    if has_demographics:
        mock_demog = MagicMock()  # Return a demographic record
        mock_demog_result.scalar_one_or_none.return_value = mock_demog
    else:
        mock_demog_result.scalar_one_or_none.return_value = None

    # Set up side_effect to return different results for sequential calls
    mock_session.execute = AsyncMock(side_effect=[mock_fin_result, mock_demog_result])
    return mock_session


def _make_fin(income=8000, debts=2500, assets=120000, credit=720):
    """Create a mock ApplicationFinancials row."""
    m = MagicMock()
    m.gross_monthly_income = income
    m.monthly_debts = debts
    m.total_assets = assets
    m.credit_score = credit
    return m


def _make_doc(doc_type: DocumentType):
    """Create a mock Document with the given type."""
    m = MagicMock()
    m.doc_type = doc_type
    return m


class TestComplianceCheckEcoa:
    """ECOA check via tool."""

    @pytest.mark.asyncio
    async def test_compliance_check_ecoa_pass(self):
        """App in UNDERWRITING -> ECOA PASS."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin()])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ECOA", "state": state}
            )

        assert "ECOA:" in result
        assert "PASS" in result
        assert "financial factors" in result.lower()


class TestComplianceCheckAtrQm:
    """ATR/QM check via tool."""

    @pytest.mark.asyncio
    async def test_compliance_check_atr_qm_pass(self):
        """Good financials + docs -> ATR/QM PASS."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        docs = [
            _make_doc(DocumentType.W2),
            _make_doc(DocumentType.BANK_STATEMENT),
        ]

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=(docs, 2),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins(
                [_make_fin(income=10000, debts=3000)]  # DTI = 0.30
            )
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ATR_QM", "state": state}
            )

        assert "ATR/QM:" in result
        assert "PASS" in result

    @pytest.mark.asyncio
    async def test_compliance_check_atr_qm_fail_high_dti(self):
        """DTI > 50% -> ATR/QM FAIL."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins(
                [_make_fin(income=5000, debts=3000)]  # DTI = 0.60
            )
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ATR_QM", "state": state}
            )

        assert "ATR/QM:" in result
        assert "FAIL" in result


class TestComplianceCheckTrid:
    """TRID check via tool."""

    @pytest.mark.asyncio
    async def test_compliance_check_trid_warning_no_dates(self):
        """No LE/CD dates -> TRID WARNING."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = MagicMock()
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin()])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "TRID", "state": state}
            )

        assert "TRID:" in result
        assert "WARNING" in result


class TestComplianceCheckAll:
    """Combined (ALL) check via tool."""

    @pytest.mark.asyncio
    async def test_compliance_check_all_combined(self):
        """regulation_type=ALL -> all three checks + overall."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        docs = [_make_doc(DocumentType.W2), _make_doc(DocumentType.BANK_STATEMENT)]
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=(docs, 2),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin(income=10000, debts=3000)])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ALL", "state": state}
            )

        assert "ECOA:" in result
        assert "ATR/QM:" in result
        assert "TRID:" in result
        assert "OVERALL STATUS:" in result
        assert "CAN PROCEED:" in result


class TestComplianceCheckGuards:
    """Stage guard and not-found tests."""

    @pytest.mark.asyncio
    async def test_compliance_check_rejects_non_underwriting(self):
        """App in APPLICATION stage -> error message."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.APPLICATION

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ALL", "state": state}
            )

        assert "only available for applications in the UNDERWRITING" in result

    @pytest.mark.asyncio
    async def test_compliance_check_app_not_found(self):
        """get_application returns None -> error message."""
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=None,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 999, "regulation_type": "ALL", "state": state}
            )

        assert "not found" in result.lower()


class TestComplianceCheckAudit:
    """Audit logging tests."""

    @pytest.mark.asyncio
    async def test_compliance_check_audits_result(self):
        """Verify write_audit_event called with event_type='compliance_check'."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin()])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ALL", "state": state}
            )

        mock_audit.assert_awaited_once()
        audit_call = mock_audit.call_args
        assert audit_call.kwargs["event_type"] == "compliance_check"
        assert audit_call.kwargs["application_id"] == 100
        event_data = audit_call.kwargs["event_data"]
        assert event_data["tool"] == "compliance_check"
        assert event_data["regulation_type"] == "ALL"
        assert "overall_status" in event_data
        assert "can_proceed" in event_data

    @pytest.mark.asyncio
    async def test_compliance_check_stage_guard_audits_error(self):
        """Stage guard writes audit event with wrong_stage error."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.APPLICATION

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ) as mock_audit,
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = AsyncMock()
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ALL", "state": state}
            )

        mock_audit.assert_awaited_once()
        assert "wrong_stage" in mock_audit.call_args.kwargs["event_data"]["error"]


# ---------------------------------------------------------------------------
# DTI aggregation and edge cases
# ---------------------------------------------------------------------------


class TestComplianceCheckDtiAggregation:
    """Tests for DTI computation from financials rows in the tool."""

    @pytest.mark.asyncio
    async def test_multi_borrower_financials_aggregation(self):
        """Two financials rows aggregate income/debts for combined DTI."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        docs = [_make_doc(DocumentType.W2), _make_doc(DocumentType.BANK_STATEMENT)]
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=(docs, 2),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            # Primary: income=8000, debts=2000; Co-borrower: income=4000, debts=1500
            # Combined DTI = 3500/12000 = 0.2917 -> PASS
            mock_session = _mock_session_with_fins(
                [
                    _make_fin(income=8000, debts=2000),
                    _make_fin(income=4000, debts=1500),
                ]
            )
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ATR_QM", "state": state}
            )

        assert "PASS" in result
        assert "29." in result  # DTI ~29.2%

    @pytest.mark.asyncio
    async def test_zero_income_produces_fail_not_crash(self):
        """Financials with zero income -> DTI=None -> ATR/QM FAIL, no ZeroDivisionError."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin(income=0, debts=2000)])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ATR_QM", "state": state}
            )

        assert "FAIL" in result
        assert "cannot be computed" in result.lower()

    @pytest.mark.asyncio
    async def test_none_income_and_debts_handled(self):
        """Financials with None income/debts -> DTI=None, no TypeError."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin(income=None, debts=None)])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ATR_QM", "state": state}
            )

        assert "FAIL" in result


# ---------------------------------------------------------------------------
# Validation and output format
# ---------------------------------------------------------------------------


class TestComplianceCheckValidation:
    """Input validation and output format tests."""

    @pytest.mark.asyncio
    async def test_invalid_regulation_type(self):
        """Invalid regulation_type returns error without touching DB."""
        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        result = await compliance_check.ainvoke(
            {"application_id": 100, "regulation_type": "HMDA", "state": state}
        )

        assert "invalid" in result.lower()
        assert "HMDA" in result

    @pytest.mark.asyncio
    async def test_single_regulation_omits_overall_section(self):
        """Single-regulation check should NOT include OVERALL STATUS."""
        mock_app = MagicMock()
        mock_app.stage = ApplicationStage.UNDERWRITING
        mock_app.created_at = None
        mock_app.le_delivery_date = None
        mock_app.cd_delivery_date = None
        mock_app.closing_date = None

        state = {"user_id": "uw-maria", "user_role": "underwriter"}

        with (
            patch(
                "src.agents.compliance_check_tool.get_application",
                new_callable=AsyncMock,
                return_value=mock_app,
            ),
            patch(
                "src.agents.compliance_check_tool.list_documents",
                new_callable=AsyncMock,
                return_value=([], 0),
            ),
            patch(
                "src.agents.compliance_check_tool.write_audit_event",
                new_callable=AsyncMock,
            ),
            patch("src.agents.compliance_check_tool.SessionLocal") as mock_session_cls,
        ):
            mock_session = _mock_session_with_fins([_make_fin()])
            mock_session_cls.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session_cls.return_value.__aexit__ = AsyncMock(return_value=False)

            result = await compliance_check.ainvoke(
                {"application_id": 100, "regulation_type": "ECOA", "state": state}
            )

        assert "ECOA:" in result
        assert "OVERALL STATUS:" not in result
        assert "CAN PROCEED:" not in result
