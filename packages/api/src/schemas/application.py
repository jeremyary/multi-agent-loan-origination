# This project was developed with assistance from AI tools.
"""Application request/response schemas."""

from datetime import datetime
from decimal import Decimal

from db.enums import ApplicationStage, EmploymentStatus, LoanType
from pydantic import BaseModel, ConfigDict, Field

from . import Pagination


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
    ssn: str | None = None
    dob: datetime | None = None
    employment_status: EmploymentStatus | None = None
    is_primary: bool = False


class ApplicationResponse(BaseModel):
    """Single application response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    stage: ApplicationStage
    loan_type: LoanType | None = None
    property_address: str | None = None
    loan_amount: Decimal | None = None
    property_value: Decimal | None = None
    assigned_to: str | None = None
    created_at: datetime
    updated_at: datetime
    borrowers: list[BorrowerSummary] = []


class ApplicationListResponse(BaseModel):
    """Paginated list of applications."""

    data: list[ApplicationResponse]
    pagination: Pagination


class AddBorrowerRequest(BaseModel):
    """Add a borrower to an application."""

    borrower_id: int
    is_primary: bool = False
