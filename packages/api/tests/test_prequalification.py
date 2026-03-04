# This project was developed with assistance from AI tools.
"""Tests for pre-qualification evaluation service."""

from decimal import Decimal

from src.services.prequalification import evaluate_prequalification


class TestEligibility:
    """Product eligibility evaluation tests."""

    def test_should_qualify_strong_borrower_for_multiple_products(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1500"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        assert len(result.eligible_products) >= 3
        eligible_ids = [p.product_id for p in result.eligible_products]
        assert "conventional_30" in eligible_ids
        assert "fha" in eligible_ids

    def test_should_reject_low_credit_score_for_conventional(self):
        result = evaluate_prequalification(
            credit_score=580,
            gross_monthly_income=Decimal("8000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("200000"),
            property_value=Decimal("250000"),
        )

        conv_results = [p for p in result.ineligible_products if p.product_id == "conventional_30"]
        assert len(conv_results) == 1
        assert "Credit score" in conv_results[0].ineligibility_reasons[0]

    def test_should_allow_fha_at_580_credit(self):
        result = evaluate_prequalification(
            credit_score=580,
            gross_monthly_income=Decimal("8000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("200000"),
            property_value=Decimal("250000"),
        )

        fha = [p for p in result.eligible_products if p.product_id == "fha"]
        assert len(fha) == 1
        assert fha[0].is_eligible

    def test_should_reject_high_dti(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("5000"),
            monthly_debts=Decimal("3000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        # With $3000 debts on $5000 income, DTI will be very high
        for p in result.ineligible_products:
            dti_reasons = [r for r in p.ineligibility_reasons if "DTI" in r]
            if dti_reasons:
                assert "exceeds" in dti_reasons[0]

    def test_should_reject_high_ltv(self):
        # 95% LTV -- exceeds jumbo's 90% max
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("15000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("475000"),
            property_value=Decimal("500000"),
        )

        jumbo = [p for p in result.ineligible_products if p.product_id == "jumbo"]
        assert len(jumbo) == 1
        ltv_reasons = [r for r in jumbo[0].ineligibility_reasons if "LTV" in r]
        assert len(ltv_reasons) >= 1

    def test_should_require_700_for_jumbo(self):
        result = evaluate_prequalification(
            credit_score=690,
            gross_monthly_income=Decimal("20000"),
            monthly_debts=Decimal("2000"),
            loan_amount=Decimal("400000"),
            property_value=Decimal("500000"),
        )

        jumbo = [p for p in result.ineligible_products if p.product_id == "jumbo"]
        assert len(jumbo) == 1
        assert "Credit score" in jumbo[0].ineligibility_reasons[0]


class TestRecommendation:
    """Recommendation logic tests."""

    def test_should_recommend_conventional_by_default(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1500"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        assert result.recommended_product_id == "conventional_30"

    def test_should_recommend_requested_product_when_eligible(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1500"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
            loan_type="fha",
        )

        assert result.recommended_product_id == "fha"

    def test_should_return_none_when_no_products_eligible(self):
        result = evaluate_prequalification(
            credit_score=400,
            gross_monthly_income=Decimal("2000"),
            monthly_debts=Decimal("1800"),
            loan_amount=Decimal("500000"),
            property_value=Decimal("200000"),
        )

        assert result.recommended_product_id is None
        assert len(result.eligible_products) == 0


class TestRatios:
    """DTI, LTV, and down payment calculation tests."""

    def test_should_compute_correct_ltv(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("320000"),
            property_value=Decimal("400000"),
        )

        assert result.ltv_ratio == 80.0
        assert result.down_payment_pct == 20.0

    def test_should_compute_dti(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("2000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        # DTI should include debts + housing payment
        assert result.dti_ratio > 20.0


class TestMaxLoanAmount:
    """Max loan amount computation tests."""

    def test_should_return_positive_max_loan_for_eligible(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        for p in result.eligible_products:
            assert p.max_loan_amount > 0

    def test_should_return_zero_max_loan_for_ineligible(self):
        result = evaluate_prequalification(
            credit_score=400,
            gross_monthly_income=Decimal("2000"),
            monthly_debts=Decimal("1800"),
            loan_amount=Decimal("500000"),
            property_value=Decimal("200000"),
        )

        for p in result.ineligible_products:
            assert p.max_loan_amount == 0

    def test_should_include_monthly_payment_for_eligible(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        for p in result.eligible_products:
            assert p.estimated_monthly_payment > 0


class TestSummary:
    """Summary text tests."""

    def test_should_include_count_in_summary_when_eligible(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1500"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
        )

        assert "Pre-qualified" in result.summary
        assert "product" in result.summary

    def test_should_suggest_improvements_when_ineligible(self):
        result = evaluate_prequalification(
            credit_score=400,
            gross_monthly_income=Decimal("2000"),
            monthly_debts=Decimal("1800"),
            loan_amount=Decimal("500000"),
            property_value=Decimal("200000"),
        )

        assert "no products" in result.summary.lower()


class TestSingleProductEvaluation:
    """Tests for loan_type filter."""

    def test_should_evaluate_only_specified_product(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
            loan_type="conventional_30",
        )

        total = len(result.eligible_products) + len(result.ineligible_products)
        assert total == 1

    def test_should_return_empty_for_unknown_product(self):
        result = evaluate_prequalification(
            credit_score=750,
            gross_monthly_income=Decimal("10000"),
            monthly_debts=Decimal("1000"),
            loan_amount=Decimal("300000"),
            property_value=Decimal("400000"),
            loan_type="nonexistent",
        )

        assert len(result.eligible_products) == 0
        assert len(result.ineligible_products) == 0
