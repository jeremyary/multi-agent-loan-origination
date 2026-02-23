# This project was developed with assistance from AI tools.
"""Affordability calculator schemas."""

from pydantic import BaseModel, Field


class AffordabilityRequest(BaseModel):
    """Input for the affordability calculator."""

    gross_annual_income: float = Field(gt=0)
    monthly_debts: float = Field(ge=0)
    down_payment: float = Field(ge=0)
    interest_rate: float = Field(default=6.5, ge=0, le=15)
    loan_term_years: int = Field(default=30, ge=10, le=40)


class AffordabilityResponse(BaseModel):
    """Affordability calculation results."""

    max_loan_amount: float
    estimated_monthly_payment: float
    estimated_purchase_price: float
    dti_ratio: float
    dti_warning: str | None = None
    pmi_warning: str | None = None
