# This project was developed with assistance from AI tools.
"""Public API routes -- no authentication required."""

from fastapi import APIRouter

from ..schemas.calculator import AffordabilityRequest, AffordabilityResponse
from ..schemas.products import ProductInfo

router = APIRouter()

PRODUCTS: list[ProductInfo] = [
    ProductInfo(
        id="conventional_30",
        name="30-Year Fixed Conventional",
        description="Standard fixed-rate mortgage with predictable monthly payments over 30 years. "
        "Ideal for buyers planning to stay long-term.",
        min_down_payment_pct=3.0,
        typical_rate=6.5,
    ),
    ProductInfo(
        id="conventional_15",
        name="15-Year Fixed Conventional",
        description="Fixed-rate mortgage with a shorter term. Higher monthly payments but "
        "significantly less total interest paid.",
        min_down_payment_pct=3.0,
        typical_rate=5.75,
    ),
    ProductInfo(
        id="fha",
        name="FHA Loan",
        description="Government-backed loan with lower credit score and down payment requirements. "
        "Requires mortgage insurance premium (MIP).",
        min_down_payment_pct=3.5,
        typical_rate=6.25,
    ),
    ProductInfo(
        id="va",
        name="VA Loan",
        description="Available to eligible veterans and service members. No down payment required "
        "and no private mortgage insurance.",
        min_down_payment_pct=0.0,
        typical_rate=6.0,
    ),
    ProductInfo(
        id="jumbo",
        name="Jumbo Loan",
        description="For loan amounts exceeding conforming limits. Typically requires higher credit "
        "scores and larger down payments.",
        min_down_payment_pct=10.0,
        typical_rate=6.75,
    ),
    ProductInfo(
        id="usda",
        name="USDA Loan",
        description="Zero down payment loan for eligible rural and suburban properties. "
        "Income limits apply.",
        min_down_payment_pct=0.0,
        typical_rate=6.25,
    ),
]


@router.get("/products", response_model=list[ProductInfo])
async def list_products() -> list[ProductInfo]:
    """Return available mortgage products. No authentication required."""
    return PRODUCTS


@router.post("/calculate-affordability", response_model=AffordabilityResponse)
async def calculate_affordability(req: AffordabilityRequest) -> AffordabilityResponse:
    """Estimate maximum loan amount and monthly payment.

    Calculation: max housing payment = gross_monthly_income * 0.43 - monthly_debts,
    then derive max loan from that payment using the standard amortization formula.
    """
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

    # Monthly interest rate and number of payments
    monthly_rate = req.interest_rate / 100 / 12
    n_payments = req.loan_term_years * 12

    # Loan constant: payment per dollar borrowed
    # P = L * [r(1+r)^n] / [(1+r)^n - 1]
    if monthly_rate > 0:
        compound = (1 + monthly_rate) ** n_payments
        payment_per_dollar = monthly_rate * compound / (compound - 1)
    else:
        payment_per_dollar = 1 / n_payments

    max_loan_amount = max_housing_payment / payment_per_dollar
    estimated_monthly_payment = max_housing_payment
    estimated_purchase_price = max_loan_amount + req.down_payment

    # DTI ratio
    total_monthly_obligations = req.monthly_debts + estimated_monthly_payment
    dti_ratio = round(total_monthly_obligations / gross_monthly_income * 100, 1)

    # Warnings
    dti_warning = None
    if dti_ratio > 43:
        dti_warning = (
            f"Your estimated DTI of {dti_ratio}% exceeds the 43% guideline "
            "for conventional loans."
        )

    pmi_warning = None
    if estimated_purchase_price > 0:
        down_pct = req.down_payment / estimated_purchase_price * 100
        if down_pct < 3:
            pmi_warning = (
                f"A down payment of {down_pct:.1f}% is below 3% of the estimated "
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
