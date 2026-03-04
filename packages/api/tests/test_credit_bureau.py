# This project was developed with assistance from AI tools.
"""Tests for mock credit bureau service."""

from decimal import Decimal

from src.services.credit_bureau import CreditBureauService
from src.services.seed.fixtures import (
    DANIEL_RAMIREZ_ID,
    EMILY_RODRIGUEZ_ID,
    SARAH_MITCHELL_ID,
    THOMAS_NGUYEN_ID,
)


def _service():
    return CreditBureauService()


class TestSoftPull:
    """Soft credit pull tests."""

    def test_should_return_seed_profile_for_known_user(self):
        result = _service().soft_pull(borrower_id=1, keycloak_user_id=SARAH_MITCHELL_ID)

        assert result.credit_score == 742
        assert result.bureau == "mock_equifax"
        assert result.outstanding_accounts == 4
        assert result.total_outstanding_debt == Decimal("45200.00")
        assert result.derogatory_marks == 0
        assert result.oldest_account_years == 12

    def test_should_return_generated_profile_when_no_keycloak_id(self):
        result = _service().soft_pull(borrower_id=42)

        assert 300 <= result.credit_score <= 850
        assert result.bureau == "mock_equifax"
        assert result.outstanding_accounts >= 2
        assert result.total_outstanding_debt > 0
        assert result.derogatory_marks >= 0
        assert result.oldest_account_years >= 2

    def test_should_return_deterministic_results_for_same_borrower(self):
        svc = _service()
        result1 = svc.soft_pull(borrower_id=99)
        result2 = svc.soft_pull(borrower_id=99)

        assert result1.credit_score == result2.credit_score
        assert result1.outstanding_accounts == result2.outstanding_accounts
        assert result1.total_outstanding_debt == result2.total_outstanding_debt

    def test_should_return_different_results_for_different_borrowers(self):
        svc = _service()
        result1 = svc.soft_pull(borrower_id=100)
        result2 = svc.soft_pull(borrower_id=200)

        # At least one field should differ (statistically guaranteed by hash)
        fields_differ = (
            result1.credit_score != result2.credit_score
            or result1.outstanding_accounts != result2.outstanding_accounts
            or result1.total_outstanding_debt != result2.total_outstanding_debt
        )
        assert fields_differ

    def test_should_return_seed_profile_for_low_credit_borrower(self):
        result = _service().soft_pull(borrower_id=1, keycloak_user_id=DANIEL_RAMIREZ_ID)

        assert result.credit_score == 612
        assert result.derogatory_marks == 3

    def test_should_return_seed_profile_for_emily_rodriguez(self):
        result = _service().soft_pull(borrower_id=1, keycloak_user_id=EMILY_RODRIGUEZ_ID)

        assert result.credit_score == 688
        assert result.derogatory_marks == 1

    def test_should_generate_when_keycloak_id_unknown(self):
        result = _service().soft_pull(borrower_id=5, keycloak_user_id="unknown-id")

        # Unknown keycloak ID falls back to hash-based generation
        assert 300 <= result.credit_score <= 850


class TestHardPull:
    """Hard credit pull tests."""

    def test_should_include_trade_lines(self):
        result = _service().hard_pull(borrower_id=1, keycloak_user_id=SARAH_MITCHELL_ID)

        assert result.credit_score == 742
        assert len(result.trade_lines) > 0
        assert result.collections_count >= 0
        assert isinstance(result.bankruptcy_flag, bool)
        assert result.public_records_count >= 0

    def test_should_have_valid_trade_line_fields(self):
        result = _service().hard_pull(borrower_id=1, keycloak_user_id=SARAH_MITCHELL_ID)

        for line in result.trade_lines:
            assert line.account_type
            assert line.balance >= 0
            assert line.monthly_payment >= 0
            assert line.status in {"current", "late_30", "late_60", "late_90", "collection"}
            assert line.opened_years_ago >= 1

    def test_should_not_flag_bankruptcy_for_good_credit(self):
        result = _service().hard_pull(borrower_id=1, keycloak_user_id=THOMAS_NGUYEN_ID)

        assert result.bankruptcy_flag is False

    def test_should_include_soft_pull_fields(self):
        svc = _service()
        hard = svc.hard_pull(borrower_id=1, keycloak_user_id=SARAH_MITCHELL_ID)
        soft = svc.soft_pull(borrower_id=1, keycloak_user_id=SARAH_MITCHELL_ID)

        assert hard.credit_score == soft.credit_score
        assert hard.outstanding_accounts == soft.outstanding_accounts
        assert hard.total_outstanding_debt == soft.total_outstanding_debt
        assert hard.derogatory_marks == soft.derogatory_marks

    def test_should_return_collections_for_low_credit(self):
        result = _service().hard_pull(borrower_id=1, keycloak_user_id=DANIEL_RAMIREZ_ID)

        # 612 score, 3 derogatory marks -> collections_count = max(0, 3-1) = 2
        assert result.collections_count == 2
        assert result.derogatory_marks == 3


class TestSingleton:
    """Singleton accessor tests."""

    def test_should_return_same_instance(self):
        from src.services.credit_bureau import get_credit_bureau_service

        svc1 = get_credit_bureau_service()
        svc2 = get_credit_bureau_service()

        assert svc1 is svc2
        assert isinstance(svc1, CreditBureauService)
