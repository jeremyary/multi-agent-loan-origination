# This project was developed with assistance from AI tools.
"""Unit tests for compliance check pure functions.

No DB, no mocking -- pure function tests for ECOA, ATR/QM, TRID,
and the combined runner.
"""

from datetime import UTC, datetime

from src.services.compliance.checks import (
    ComplianceStatus,
    _business_days_between,
    check_atr_qm,
    check_ecoa,
    check_trid,
    run_all_checks,
)

# ---------------------------------------------------------------------------
# ECOA
# ---------------------------------------------------------------------------


class TestCheckEcoa:
    """ECOA compliance check tests."""

    def test_ecoa_pass(self):
        """Default (no demographic query) -> PASS."""
        result = check_ecoa()
        assert result.status == ComplianceStatus.PASS
        assert result.regulation == "ECOA"
        assert "financial factors" in result.rationale.lower()

    def test_ecoa_warning_demographic_query(self):
        """Demographic query attempted -> WARNING."""
        result = check_ecoa(has_demographic_query=True)
        assert result.status == ComplianceStatus.WARNING
        assert "attempted and refused" in result.rationale.lower()


# ---------------------------------------------------------------------------
# ATR/QM
# ---------------------------------------------------------------------------


class TestCheckAtrQm:
    """ATR/QM compliance check tests."""

    def test_atr_qm_pass_low_dti_all_docs(self):
        """DTI=0.38, all docs present -> PASS."""
        result = check_atr_qm(
            dti=0.38,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.PASS
        assert result.regulation == "ATR/QM"
        assert "safe harbor" in result.rationale.lower()

    def test_atr_qm_conditional_pass_elevated_dti(self):
        """DTI=0.46 -> CONDITIONAL_PASS."""
        result = check_atr_qm(
            dti=0.46,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.CONDITIONAL_PASS
        assert "rebuttable presumption" in result.rationale.lower()

    def test_atr_qm_fail_extreme_dti(self):
        """DTI=0.55 -> FAIL."""
        result = check_atr_qm(
            dti=0.55,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.FAIL
        assert "50%" in result.rationale

    def test_atr_qm_fail_no_dti(self):
        """DTI=None -> FAIL."""
        result = check_atr_qm(
            dti=None,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.FAIL
        assert "cannot be computed" in result.rationale.lower()

    def test_atr_qm_warning_missing_income_docs(self):
        """Good DTI but missing income docs -> WARNING."""
        result = check_atr_qm(
            dti=0.35,
            has_income_docs=False,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.WARNING
        assert any("income" in d.lower() for d in result.details)

    def test_atr_qm_warning_missing_asset_docs(self):
        """Good DTI but missing asset docs -> WARNING."""
        result = check_atr_qm(
            dti=0.35,
            has_income_docs=True,
            has_asset_docs=False,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.WARNING
        assert any("asset" in d.lower() for d in result.details)

    def test_atr_qm_boundary_at_043(self):
        """DTI exactly 0.43, all docs -> PASS (boundary)."""
        result = check_atr_qm(
            dti=0.43,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.PASS

    def test_atr_qm_boundary_at_050(self):
        """DTI exactly 0.50 -> CONDITIONAL_PASS (boundary)."""
        result = check_atr_qm(
            dti=0.50,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.CONDITIONAL_PASS

    def test_atr_qm_elevated_dti_with_missing_docs(self):
        """DTI in rebuttable-presumption range + missing docs -> CONDITIONAL_PASS.

        Documents the design choice: DTI 0.43-0.50 drives CONDITIONAL_PASS
        regardless of doc completeness. Missing-doc details are still appended
        but don't override the DTI-driven status.
        """
        result = check_atr_qm(
            dti=0.46,
            has_income_docs=False,
            has_asset_docs=True,
            has_employment_docs=True,
        )
        assert result.status == ComplianceStatus.CONDITIONAL_PASS
        assert any("income" in d.lower() for d in result.details)
        assert any("rebuttable" in d.lower() for d in result.details)

    def test_atr_qm_no_dti_no_docs(self):
        """No DTI + no docs -> FAIL with missing-doc details (not fallback msg)."""
        result = check_atr_qm(
            dti=None,
            has_income_docs=False,
            has_asset_docs=False,
            has_employment_docs=False,
        )
        assert result.status == ComplianceStatus.FAIL
        assert any("income" in d.lower() for d in result.details)
        assert any("asset" in d.lower() for d in result.details)
        assert any("employment" in d.lower() for d in result.details)

    def test_atr_qm_warning_missing_employment_docs_only(self):
        """Good DTI + only employment docs missing -> WARNING.

        Exercises the case where W2 counts as income but a borrower who
        submitted only TAX_RETURN (income) + BANK_STATEMENT (asset) has
        no employment verification.
        """
        result = check_atr_qm(
            dti=0.35,
            has_income_docs=True,
            has_asset_docs=True,
            has_employment_docs=False,
        )
        assert result.status == ComplianceStatus.WARNING
        assert any("employment" in d.lower() for d in result.details)


# ---------------------------------------------------------------------------
# TRID
# ---------------------------------------------------------------------------


class TestCheckTrid:
    """TRID compliance check tests."""

    def test_trid_pass_le_on_time(self):
        """LE delivered within 2 business days -> PASS."""
        # Monday -> Wednesday = 2 business days
        app_created = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        le_delivered = datetime(2026, 3, 4, 10, 0, tzinfo=UTC)  # Wed
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=None,
        )
        assert result.status == ComplianceStatus.PASS
        assert any("on time" in d.lower() for d in result.details)

    def test_trid_fail_le_late(self):
        """LE delivered after 5 business days -> FAIL."""
        # Mon -> Mon next week = 5 business days
        app_created = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        le_delivered = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)  # Mon
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=None,
        )
        assert result.status == ComplianceStatus.FAIL
        assert any("exceeds" in d.lower() for d in result.details)

    def test_trid_warning_no_le_date(self):
        """le_delivery_date=None -> WARNING."""
        app_created = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=None,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=None,
        )
        assert result.status == ComplianceStatus.WARNING
        assert any("not yet delivered" in d.lower() for d in result.details)

    def test_trid_pass_cd_on_time(self):
        """CD delivered 5 business days before closing -> PASS."""
        # Mon -> Mon next week = 5 business days
        cd_delivered = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        closing = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)  # Mon
        app_created = datetime(2026, 2, 20, 10, 0, tzinfo=UTC)
        le_delivered = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=cd_delivered,
            closing_date=closing,
        )
        assert result.status == ComplianceStatus.PASS
        assert any("on time" in d.lower() for d in result.details if "closing" in d.lower())

    def test_trid_fail_cd_late(self):
        """CD delivered 1 business day before closing -> FAIL."""
        # Thu -> Fri = 1 business day
        cd_delivered = datetime(2026, 3, 5, 10, 0, tzinfo=UTC)  # Thu
        closing = datetime(2026, 3, 6, 10, 0, tzinfo=UTC)  # Fri
        app_created = datetime(2026, 2, 20, 10, 0, tzinfo=UTC)
        le_delivered = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=cd_delivered,
            closing_date=closing,
        )
        assert result.status == ComplianceStatus.FAIL
        assert any("must be at least 3" in d.lower() for d in result.details)

    def test_trid_warning_no_cd_with_closing(self):
        """Closing scheduled but CD not delivered -> WARNING."""
        closing = datetime(2026, 3, 15, 10, 0, tzinfo=UTC)
        app_created = datetime(2026, 2, 20, 10, 0, tzinfo=UTC)
        le_delivered = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=closing,
        )
        assert result.status == ComplianceStatus.WARNING
        assert any("not yet delivered" in d.lower() for d in result.details)

    def test_trid_pass_no_closing_date(self):
        """No closing scheduled -> CD timing is N/A, overall PASS."""
        app_created = datetime(2026, 2, 20, 10, 0, tzinfo=UTC)
        le_delivered = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=None,
        )
        assert result.status == ComplianceStatus.PASS

    def test_trid_pass_le_at_exactly_3_business_days(self):
        """LE delivered at exactly the 3-business-day boundary -> PASS."""
        # Mon -> Thu = exactly 3 business days
        app_created = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        le_delivered = datetime(2026, 3, 5, 10, 0, tzinfo=UTC)  # Thu
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=None,
            closing_date=None,
        )
        assert result.status == ComplianceStatus.PASS

    def test_trid_pass_cd_at_exactly_3_business_days(self):
        """CD delivered exactly 3 business days before closing -> PASS."""
        # Mon -> Thu = 3 business days
        cd_delivered = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        closing = datetime(2026, 3, 5, 10, 0, tzinfo=UTC)  # Thu
        app_created = datetime(2026, 2, 20, 10, 0, tzinfo=UTC)
        le_delivered = datetime(2026, 2, 22, 10, 0, tzinfo=UTC)
        result = check_trid(
            le_delivery_date=le_delivered,
            app_created_at=app_created,
            cd_delivery_date=cd_delivered,
            closing_date=closing,
        )
        assert result.status == ComplianceStatus.PASS


# ---------------------------------------------------------------------------
# Combined runner
# ---------------------------------------------------------------------------


class TestRunAllChecks:
    """Tests for the combined compliance check runner."""

    def test_run_all_overall_pass(self):
        """All PASS -> overall PASS, can_proceed=True."""
        ecoa = check_ecoa()
        atr = check_atr_qm(
            dti=0.35, has_income_docs=True, has_asset_docs=True, has_employment_docs=True
        )
        trid_result = check_trid(
            le_delivery_date=datetime(2026, 2, 22, 10, 0, tzinfo=UTC),
            app_created_at=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
            cd_delivery_date=None,
            closing_date=None,
        )
        combined = run_all_checks(ecoa, atr, trid_result)
        assert combined["overall_status"] == ComplianceStatus.PASS
        assert combined["can_proceed"] is True
        assert len(combined["checks"]) == 3

    def test_run_all_overall_fail(self):
        """One FAIL -> overall FAIL, can_proceed=False."""
        ecoa = check_ecoa()
        atr = check_atr_qm(
            dti=0.55, has_income_docs=True, has_asset_docs=True, has_employment_docs=True
        )
        trid_result = check_trid(
            le_delivery_date=datetime(2026, 2, 22, 10, 0, tzinfo=UTC),
            app_created_at=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
            cd_delivery_date=None,
            closing_date=None,
        )
        combined = run_all_checks(ecoa, atr, trid_result)
        assert combined["overall_status"] == ComplianceStatus.FAIL
        assert combined["can_proceed"] is False

    def test_run_all_overall_warning(self):
        """One WARNING, no FAIL -> overall WARNING, can_proceed=True."""
        ecoa = check_ecoa(has_demographic_query=True)  # WARNING
        atr = check_atr_qm(
            dti=0.35, has_income_docs=True, has_asset_docs=True, has_employment_docs=True
        )
        trid_result = check_trid(
            le_delivery_date=datetime(2026, 2, 22, 10, 0, tzinfo=UTC),
            app_created_at=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
            cd_delivery_date=None,
            closing_date=None,
        )
        combined = run_all_checks(ecoa, atr, trid_result)
        assert combined["overall_status"] == ComplianceStatus.WARNING
        assert combined["can_proceed"] is True

    def test_run_all_overall_conditional_pass(self):
        """CONDITIONAL_PASS as worst status -> overall CONDITIONAL_PASS, can_proceed=True."""
        ecoa = check_ecoa()  # PASS
        atr = check_atr_qm(
            dti=0.46, has_income_docs=True, has_asset_docs=True, has_employment_docs=True
        )  # CONDITIONAL_PASS
        trid_result = check_trid(
            le_delivery_date=datetime(2026, 2, 22, 10, 0, tzinfo=UTC),
            app_created_at=datetime(2026, 2, 20, 10, 0, tzinfo=UTC),
            cd_delivery_date=None,
            closing_date=None,
        )  # PASS
        combined = run_all_checks(ecoa, atr, trid_result)
        assert combined["overall_status"] == ComplianceStatus.CONDITIONAL_PASS
        assert combined["can_proceed"] is True


# ---------------------------------------------------------------------------
# Business days helper
# ---------------------------------------------------------------------------


class TestBusinessDaysBetween:
    """Tests for the _business_days_between helper."""

    def test_business_days_weekday_span(self):
        """Mon -> Fri = 4 business days."""
        start = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        end = datetime(2026, 3, 6, 10, 0, tzinfo=UTC)  # Fri
        assert _business_days_between(start, end) == 4

    def test_business_days_across_weekend(self):
        """Fri -> Mon = 1 business day (skips Sat/Sun)."""
        start = datetime(2026, 3, 6, 10, 0, tzinfo=UTC)  # Fri
        end = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)  # Mon
        assert _business_days_between(start, end) == 1

    def test_business_days_same_day(self):
        """Same day -> 0 business days."""
        d = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)
        assert _business_days_between(d, d) == 0

    def test_business_days_full_week(self):
        """Mon -> Mon (next week) = 5 business days."""
        start = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)  # Mon
        end = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)  # Mon
        assert _business_days_between(start, end) == 5

    def test_business_days_end_before_start(self):
        """End before start -> 0 (handles data entry errors gracefully)."""
        start = datetime(2026, 3, 9, 10, 0, tzinfo=UTC)
        end = datetime(2026, 3, 2, 10, 0, tzinfo=UTC)
        assert _business_days_between(start, end) == 0
