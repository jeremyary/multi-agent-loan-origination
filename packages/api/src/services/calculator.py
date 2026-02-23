# This project was developed with assistance from AI tools.
"""Affordability calculation logic.

Pure math, no I/O. Shared by the public API route and the agent tool.
"""

from ..schemas.calculator import AffordabilityRequest, AffordabilityResponse


def calculate_affordability(req: AffordabilityRequest) -> AffordabilityResponse:
    """Estimate maximum loan amount and monthly payment."""
    gross_monthly_income = req.gross_annual_income / 12
    max_housing_payment = gross_monthly_income * 0.43 - req.monthly_debts

    if max_housing_payment <= 0:
        return AffordabilityResponse(
            max_loan_amount=0,
            estimated_monthly_payment=0,
            estimated_purchase_price=req.down_payment,
            dti_ratio=round(req.monthly_debts / gross_monthly_income * 100, 1)
            if gross_monthly_income > 0
            else 0,
            dti_warning="Your existing debts already exceed 43% of gross income.",
        )

    monthly_rate = req.interest_rate / 100 / 12
    n_payments = req.loan_term_years * 12

    if monthly_rate > 0:
        compound = (1 + monthly_rate) ** n_payments
        payment_per_dollar = monthly_rate * compound / (compound - 1)
    else:
        payment_per_dollar = 1 / n_payments

    max_loan_amount = max_housing_payment / payment_per_dollar
    estimated_monthly_payment = max_housing_payment
    estimated_purchase_price = max_loan_amount + req.down_payment

    total_monthly_obligations = req.monthly_debts + estimated_monthly_payment
    dti_ratio = round(total_monthly_obligations / gross_monthly_income * 100, 1)

    dti_warning = None
    if dti_ratio > 43:
        dti_warning = (
            f"Your estimated DTI of {dti_ratio}% exceeds the 43% guideline for conventional loans."
        )

    pmi_warning = None
    if estimated_purchase_price > 0:
        down_pct = req.down_payment / estimated_purchase_price * 100
        if down_pct < 20:
            pmi_warning = (
                f"A down payment of {down_pct:.1f}% is below 20% of the estimated "
                "purchase price and may require private mortgage insurance (PMI)."
            )

    return AffordabilityResponse(
        max_loan_amount=round(max_loan_amount, 2),
        estimated_monthly_payment=round(estimated_monthly_payment, 2),
        estimated_purchase_price=round(estimated_purchase_price, 2),
        dti_ratio=dti_ratio,
        dti_warning=dti_warning,
        pmi_warning=pmi_warning,
    )
