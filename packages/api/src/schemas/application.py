# This project was developed with assistance from AI tools.
"""Application request/response schemas."""

from datetime import datetime
from decimal import Decimal

from db.enums import ApplicationStage, LoanType
from pydantic import BaseModel, ConfigDict, Field


class ApplicationCreate(BaseModel):
    """Create a new mortgage application."""

    loan_type: LoanType | None = None
    property_address: str | None = None
    loan_amount: Decimal | None = Field(default=None, ge=0)
    property_value: Decimal | None = Field(default=None, ge=0)


class ApplicationUpdate(BaseModel):
    """Partial update to an existing application."""

    stage: ApplicationStage | None = None
    loan_type: LoanType | None = None
    property_address: str | None = None
    loan_amount: Decimal | None = Field(default=None, ge=0)
    property_value: Decimal | None = Field(default=None, ge=0)
    assigned_to: str | None = None


class BorrowerSummary(BaseModel):
    """Borrower info nested inside application responses."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    first_name: str
    last_name: str
    email: str
    ssn_encrypted: str | None = None
    dob: datetime | None = None


class ApplicationResponse(BaseModel):
    """Single application response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    borrower_id: int
    stage: ApplicationStage
    loan_type: LoanType | None = None
    property_address: str | None = None
    loan_amount: Decimal | None = None
    property_value: Decimal | None = None
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime
    borrower: BorrowerSummary | None = None


class ApplicationListResponse(BaseModel):
    """Paginated list of applications."""

    data: list[ApplicationResponse]
    count: int
