# This project was developed with assistance from AI tools.
"""Application intake service for conversational data collection.

Handles the lifecycle of mortgage application intake: finding active
applications, creating new ones, collecting/validating field data,
and tracking collection progress.
"""

import logging
from datetime import datetime
from decimal import Decimal

from db import Application, ApplicationBorrower, ApplicationFinancials, Borrower
from db.enums import ApplicationStage, EmploymentStatus, LoanType
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..schemas.auth import UserContext
from ..services.application import create_application
from ..services.intake_validation import validate_field
from ..services.scope import apply_data_scope

logger = logging.getLogger(__name__)

# Terminal stages -- applications in these stages are not considered "active"
_TERMINAL_STAGES = {
    ApplicationStage.WITHDRAWN,
    ApplicationStage.DENIED,
    ApplicationStage.CLOSED,
}


async def find_active_application(
    session: AsyncSession,
    user: UserContext,
) -> Application | None:
    """Find the user's most recent non-terminal application.

    Returns None if the user has no active applications. Withdrawn, denied,
    and closed applications are excluded.
    """
    stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.stage.notin_([s.value for s in _TERMINAL_STAGES]))
        .order_by(Application.updated_at.desc())
        .limit(1)
    )
    stmt = apply_data_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def start_application(
    session: AsyncSession,
    user: UserContext,
) -> dict:
    """Start a new application or return an existing active one.

    Returns a dict with:
        - application_id: The application ID
        - stage: Current stage
        - is_new: True if a new application was created
    """
    existing = await find_active_application(session, user)
    if existing is not None:
        return {
            "application_id": existing.id,
            "stage": existing.stage.value
            if isinstance(existing.stage, ApplicationStage)
            else existing.stage,
            "is_new": False,
        }

    app = await create_application(session, user)
    return {
        "application_id": app.id,
        "stage": app.stage.value if isinstance(app.stage, ApplicationStage) else app.stage,
        "is_new": True,
    }


# ---------------------------------------------------------------------------
# Field-to-table routing
# ---------------------------------------------------------------------------
# Maps field names to (table, column, converter) where converter transforms
# the validated string into the column's Python type.


def _decimal(v: str) -> Decimal:
    return Decimal(v)


def _int(v: str) -> int:
    return int(v)


def _date(v: str) -> datetime:
    return datetime.fromisoformat(v)


def _loan_type(v: str) -> LoanType:
    return LoanType(v)


def _employment_status(v: str) -> EmploymentStatus:
    return EmploymentStatus(v)


def _identity(v: str) -> str:
    return v


REQUIRED_FIELDS: dict[str, tuple[str, str, callable]] = {
    # Application fields
    "loan_type": ("application", "loan_type", _loan_type),
    "property_address": ("application", "property_address", _identity),
    "loan_amount": ("application", "loan_amount", _decimal),
    "property_value": ("application", "property_value", _decimal),
    # Borrower fields
    "first_name": ("borrower", "first_name", _identity),
    "last_name": ("borrower", "last_name", _identity),
    "email": ("borrower", "email", _identity),
    "ssn": ("borrower", "ssn_encrypted", _identity),
    "date_of_birth": ("borrower", "dob", _date),
    "employment_status": ("borrower", "employment_status", _employment_status),
    # Financial fields
    "gross_monthly_income": ("financials", "gross_monthly_income", _decimal),
    "monthly_debts": ("financials", "monthly_debts", _decimal),
    "total_assets": ("financials", "total_assets", _decimal),
    "credit_score": ("financials", "credit_score", _int),
}

# Reverse lookup: column name -> field name (for reading current values)
_COLUMN_TO_FIELD: dict[str, tuple[str, str]] = {}
for _fname, (_table, _col, _) in REQUIRED_FIELDS.items():
    _COLUMN_TO_FIELD[(_table, _col)] = _fname


async def _get_borrower_for_app(
    session: AsyncSession,
    application_id: int,
    user: UserContext,
) -> Borrower | None:
    """Get the primary borrower for an application."""
    stmt = (
        select(Borrower)
        .join(ApplicationBorrower, ApplicationBorrower.borrower_id == Borrower.id)
        .where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.is_primary.is_(True),
            Borrower.keycloak_user_id == user.user_id,
        )
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


async def _get_or_create_financials(
    session: AsyncSession,
    application_id: int,
    borrower_id: int,
) -> ApplicationFinancials:
    """Get or create the financials record for an app/borrower pair."""
    stmt = select(ApplicationFinancials).where(
        ApplicationFinancials.application_id == application_id,
        ApplicationFinancials.borrower_id == borrower_id,
    )
    result = await session.execute(stmt)
    financials = result.scalar_one_or_none()
    if financials is None:
        financials = ApplicationFinancials(
            application_id=application_id,
            borrower_id=borrower_id,
        )
        session.add(financials)
        await session.flush()
    return financials


async def update_application_fields(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    fields: dict[str, str],
) -> dict:
    """Validate and persist field values for an application.

    Routes each field to the correct table (application/borrower/financials),
    validates values, and auto-computes DTI when both income and debts are present.

    Returns:
        dict with keys: updated (list of field names), errors (dict of field->msg),
        remaining (list of still-empty field names)
    """
    # Load application (with scope check)
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.financials))
    )
    stmt = apply_data_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    app = result.unique().scalar_one_or_none()
    if app is None:
        return {"updated": [], "errors": {"_": "Application not found"}, "remaining": []}

    borrower = await _get_borrower_for_app(session, application_id, user)
    if borrower is None:
        return {"updated": [], "errors": {"_": "Borrower not found"}, "remaining": []}

    financials = await _get_or_create_financials(session, application_id, borrower.id)

    updated = []
    errors = {}
    corrections = {}

    for field_name, raw_value in fields.items():
        if field_name not in REQUIRED_FIELDS:
            errors[field_name] = f"Unknown field: {field_name}"
            continue

        is_valid, error_msg, normalized = validate_field(field_name, str(raw_value))
        if not is_valid:
            errors[field_name] = error_msg
            continue

        table, column, converter = REQUIRED_FIELDS[field_name]
        converted = converter(normalized)

        # Determine target object and track corrections
        if table == "application":
            old_value = getattr(app, column, None)
            setattr(app, column, converted)
        elif table == "borrower":
            old_value = getattr(borrower, column, None)
            setattr(borrower, column, converted)
        elif table == "financials":
            old_value = getattr(financials, column, None)
            setattr(financials, column, converted)
        else:
            continue

        if old_value is not None:
            corrections[field_name] = {"old": str(old_value), "new": str(converted)}

        updated.append(field_name)

    # Auto-compute DTI when both income and debts are present
    if financials.gross_monthly_income and financials.monthly_debts:
        income = float(financials.gross_monthly_income)
        if income > 0:
            financials.dti_ratio = float(financials.monthly_debts) / income

    await session.flush()

    remaining = await get_remaining_fields(session, user, application_id)

    return {
        "updated": updated,
        "errors": errors,
        "remaining": remaining,
        "corrections": corrections,
    }


async def get_remaining_fields(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> list[str]:
    """Return list of required fields that are still empty."""
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.financials))
    )
    stmt = apply_data_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    app = result.unique().scalar_one_or_none()
    if app is None:
        return list(REQUIRED_FIELDS.keys())

    borrower = await _get_borrower_for_app(session, application_id, user)
    financials = app.financials

    remaining = []
    for field_name, (table, column, _) in REQUIRED_FIELDS.items():
        if table == "application":
            val = getattr(app, column, None)
        elif table == "borrower":
            val = getattr(borrower, column, None) if borrower else None
        elif table == "financials":
            val = getattr(financials, column, None) if financials else None
        else:
            val = None

        if val is None or (isinstance(val, str) and not val.strip()):
            remaining.append(field_name)

    return remaining
