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
    "ssn": ("borrower", "ssn", _identity),
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
        if financials.gross_monthly_income > 0:
            financials.dti_ratio = financials.monthly_debts / financials.gross_monthly_income

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
    financials = next(
        (f for f in (app.financials or []) if borrower and f.borrower_id == borrower.id),
        None,
    )

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


# ---------------------------------------------------------------------------
# Application progress / summary
# ---------------------------------------------------------------------------

# Display labels and section groupings for the summary view.
_FIELD_SECTIONS: dict[str, list[tuple[str, str]]] = {
    "Personal Information": [
        ("first_name", "First Name"),
        ("last_name", "Last Name"),
        ("email", "Email"),
        ("ssn", "SSN"),
        ("date_of_birth", "Date of Birth"),
        ("employment_status", "Employment Status"),
    ],
    "Property Information": [
        ("property_address", "Property Address"),
        ("property_value", "Property Value"),
    ],
    "Financial Information": [
        ("gross_monthly_income", "Monthly Income"),
        ("monthly_debts", "Monthly Debts"),
        ("total_assets", "Total Assets"),
        ("credit_score", "Credit Score"),
    ],
    "Loan Details": [
        ("loan_type", "Loan Type"),
        ("loan_amount", "Loan Amount"),
    ],
}


def _mask_ssn(value: str | None) -> str | None:
    """Return last-4 masked SSN, e.g. '***-**-1234'."""
    if not value:
        return None
    digits = value.replace("-", "").replace(" ", "")
    if len(digits) >= 4:
        return f"***-**-{digits[-4:]}"
    return "***"


def _format_value(field_name: str, raw) -> str | None:
    """Format a raw DB value for display. Returns None if empty."""
    if raw is None:
        return None
    if isinstance(raw, str) and not raw.strip():
        return None

    if field_name == "ssn":
        return _mask_ssn(str(raw))
    if field_name == "date_of_birth":
        if hasattr(raw, "strftime"):
            return raw.strftime("%Y-%m-%d")
        return str(raw)
    if field_name in (
        "loan_amount",
        "property_value",
        "gross_monthly_income",
        "monthly_debts",
        "total_assets",
    ):
        return f"${float(raw):,.2f}"
    if field_name == "employment_status" and hasattr(raw, "value"):
        return raw.value.replace("_", " ").title()
    if field_name == "loan_type" and hasattr(raw, "value"):
        return raw.value.replace("_", " ").title()
    return str(raw)


async def get_application_progress(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> dict | None:
    """Build a structured progress summary for an application.

    Returns None if the application is not found.  Otherwise returns::

        {
            "application_id": int,
            "stage": str,
            "sections": {<section_name>: {<label>: <value_or_None>}},
            "completed": int,
            "total": int,
            "remaining": [field_name, ...],
        }
    """
    stmt = (
        select(Application)
        .where(Application.id == application_id)
        .options(selectinload(Application.financials))
    )
    stmt = apply_data_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    app = result.unique().scalar_one_or_none()
    if app is None:
        return None

    borrower = await _get_borrower_for_app(session, application_id, user)
    financials = next(
        (f for f in (app.financials or []) if borrower and f.borrower_id == borrower.id),
        None,
    )

    sections: dict[str, dict[str, str | None]] = {}
    remaining: list[str] = []
    completed = 0
    total = len(REQUIRED_FIELDS)

    for section_name, field_list in _FIELD_SECTIONS.items():
        section_data: dict[str, str | None] = {}
        for field_name, label in field_list:
            table, column, _ = REQUIRED_FIELDS[field_name]
            if table == "application":
                raw = getattr(app, column, None)
            elif table == "borrower":
                raw = getattr(borrower, column, None) if borrower else None
            elif table == "financials":
                raw = getattr(financials, column, None) if financials else None
            else:
                raw = None

            formatted = _format_value(field_name, raw)
            section_data[label] = formatted
            if formatted is not None:
                completed += 1
            else:
                remaining.append(field_name)
        sections[section_name] = section_data

    stage = app.stage.value if isinstance(app.stage, ApplicationStage) else app.stage

    return {
        "application_id": application_id,
        "stage": stage,
        "sections": sections,
        "completed": completed,
        "total": total,
        "remaining": remaining,
    }
