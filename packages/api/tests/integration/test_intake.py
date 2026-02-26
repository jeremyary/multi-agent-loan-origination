# This project was developed with assistance from AI tools.
"""Integration tests for application intake service (S-2-F3-01 through S-2-F3-03).

Tests start_application, find_active_application, update_application_fields,
and get_remaining_fields against a real PostgreSQL instance via testcontainers.
"""

import pytest
import pytest_asyncio
from db.enums import ApplicationStage
from db.models import Application, ApplicationBorrower, ApplicationFinancials, Borrower
from sqlalchemy import select

from src.services.intake import (
    find_active_application,
    get_remaining_fields,
    start_application,
    update_application_fields,
)
from tests.functional.personas import (
    MICHAEL_USER_ID,
    SARAH_USER_ID,
    borrower_michael,
    borrower_sarah,
)


@pytest_asyncio.fixture
async def intake_seed(db_session):
    """Seed data specifically for intake tests.

    Sarah has two applications (APPLICATION + WITHDRAWN).
    Michael has none.
    """
    sarah = Borrower(
        keycloak_user_id=SARAH_USER_ID,
        first_name="Sarah",
        last_name="Mitchell",
        email="sarah@example.com",
    )
    michael = Borrower(
        keycloak_user_id=MICHAEL_USER_ID,
        first_name="Michael",
        last_name="Chen",
        email="michael@example.com",
    )
    db_session.add_all([sarah, michael])
    await db_session.flush()

    # Active application for Sarah
    active_app = Application(
        stage=ApplicationStage.APPLICATION,
        property_address="123 Main St, Denver, CO",
        loan_amount=350000,
    )
    db_session.add(active_app)
    await db_session.flush()
    db_session.add(
        ApplicationBorrower(
            application_id=active_app.id,
            borrower_id=sarah.id,
            is_primary=True,
        )
    )

    # Withdrawn application for Sarah (should be ignored)
    withdrawn_app = Application(stage=ApplicationStage.WITHDRAWN)
    db_session.add(withdrawn_app)
    await db_session.flush()
    db_session.add(
        ApplicationBorrower(
            application_id=withdrawn_app.id,
            borrower_id=sarah.id,
            is_primary=True,
        )
    )

    await db_session.flush()

    # Capture IDs eagerly to avoid MissingGreenlet after session commits
    return {
        "sarah": sarah,
        "sarah_id": sarah.id,
        "michael": michael,
        "michael_id": michael.id,
        "active_app_id": active_app.id,
        "withdrawn_app_id": withdrawn_app.id,
    }


@pytest.mark.asyncio
async def test_find_active_application_returns_active(db_session, intake_seed):
    """find_active_application returns Sarah's non-withdrawn application."""
    user = borrower_sarah()
    result = await find_active_application(db_session, user)
    assert result is not None
    assert result.id == intake_seed["active_app_id"]
    assert result.stage == ApplicationStage.APPLICATION


@pytest.mark.asyncio
async def test_find_active_application_ignores_withdrawn(db_session, intake_seed):
    """Withdrawn applications are filtered out."""
    user = borrower_sarah()
    result = await find_active_application(db_session, user)
    # Should NOT return the withdrawn app
    assert result.id != intake_seed["withdrawn_app_id"]


@pytest.mark.asyncio
async def test_find_active_application_returns_none_for_new_user(db_session, intake_seed):
    """Michael has no applications, so find returns None."""
    user = borrower_michael()
    result = await find_active_application(db_session, user)
    assert result is None


@pytest.mark.asyncio
async def test_start_application_returns_existing(db_session, intake_seed):
    """start_application returns Sarah's existing active app (no new creation)."""
    user = borrower_sarah()
    result = await start_application(db_session, user)
    assert result["is_new"] is False
    assert result["application_id"] == intake_seed["active_app_id"]
    assert result["stage"] == "application"


@pytest.mark.asyncio
async def test_start_application_creates_for_new_user(db_session, intake_seed):
    """start_application creates a new app for Michael (no active app exists)."""
    user = borrower_michael()
    result = await start_application(db_session, user)
    assert result["is_new"] is True
    assert result["stage"] == "inquiry"

    # Verify the application was actually created in the DB
    app_id = result["application_id"]
    stmt = select(Application).where(Application.id == app_id)
    row = await db_session.execute(stmt)
    app = row.scalar_one_or_none()
    assert app is not None
    assert app.stage == ApplicationStage.INQUIRY

    # Verify junction row was created
    junc_stmt = select(ApplicationBorrower).where(ApplicationBorrower.application_id == app_id)
    junc_row = await db_session.execute(junc_stmt)
    junction = junc_row.scalar_one_or_none()
    assert junction is not None
    assert junction.is_primary is True


@pytest.mark.asyncio
async def test_start_application_scope_isolation(db_session, intake_seed):
    """Michael cannot see Sarah's application -- gets a new one."""
    user = borrower_michael()
    result = await start_application(db_session, user)
    assert result["is_new"] is True
    assert result["application_id"] != intake_seed["active_app_id"]


@pytest.mark.asyncio
async def test_find_active_returns_most_recently_updated(db_session, intake_seed):
    """When multiple active apps exist, the most recently updated is returned."""
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import update

    sarah_id = intake_seed["sarah_id"]

    # Add a second active app
    newer_app = Application(
        stage=ApplicationStage.PROCESSING,
        property_address="456 Oak Ave, Denver, CO",
        loan_amount=500000,
    )
    db_session.add(newer_app)
    await db_session.flush()
    db_session.add(
        ApplicationBorrower(
            application_id=newer_app.id,
            borrower_id=sarah_id,
            is_primary=True,
        )
    )
    await db_session.flush()
    newer_app_id = newer_app.id

    # Force the newer app to have a later updated_at
    future = datetime.now(UTC) + timedelta(hours=1)
    await db_session.execute(
        update(Application).where(Application.id == newer_app_id).values(updated_at=future)
    )
    await db_session.flush()
    # Expire cached state so the query sees the updated timestamp
    db_session.expire_all()

    user = borrower_sarah()
    result = await find_active_application(db_session, user)
    assert result is not None
    assert result.id == newer_app_id


@pytest.mark.asyncio
async def test_find_active_ignores_denied_and_closed(db_session, intake_seed):
    """Denied and closed applications are also filtered out."""
    sarah_id = intake_seed["sarah_id"]

    # Add denied and closed apps
    for stage in (ApplicationStage.DENIED, ApplicationStage.CLOSED):
        app = Application(stage=stage)
        db_session.add(app)
        await db_session.flush()
        db_session.add(
            ApplicationBorrower(
                application_id=app.id,
                borrower_id=sarah_id,
                is_primary=True,
            )
        )
    await db_session.flush()

    user = borrower_sarah()
    result = await find_active_application(db_session, user)
    # Should still return only the active one, not denied/closed
    assert result is not None
    assert result.stage == ApplicationStage.APPLICATION


# ---------------------------------------------------------------------------
# update_application_fields + get_remaining_fields (S-2-F3-02, S-2-F3-03)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_update_fields_stores_values(db_session, intake_seed):
    """update_application_fields persists validated values to the correct tables."""
    user = borrower_sarah()
    app_id = intake_seed["active_app_id"]

    result = await update_application_fields(
        db_session,
        user,
        app_id,
        {
            "loan_type": "fha",
            "gross_monthly_income": "$6,250",
            "credit_score": "720",
        },
    )

    assert result["errors"] == {}
    assert set(result["updated"]) == {"loan_type", "gross_monthly_income", "credit_score"}

    # Verify values in DB
    db_session.expire_all()
    stmt = select(Application).where(Application.id == app_id)
    app = (await db_session.execute(stmt)).scalar_one()
    assert app.loan_type.value == "fha"

    fin_stmt = select(ApplicationFinancials).where(ApplicationFinancials.application_id == app_id)
    fin = (await db_session.execute(fin_stmt)).scalar_one()
    assert float(fin.gross_monthly_income) == 6250.00
    assert fin.credit_score == 720


@pytest.mark.asyncio
async def test_update_fields_validation_rejects_bad_values(db_session, intake_seed):
    """Invalid values are rejected per field while valid ones still save."""
    user = borrower_sarah()
    app_id = intake_seed["active_app_id"]

    result = await update_application_fields(
        db_session,
        user,
        app_id,
        {
            "email": "valid@example.com",
            "credit_score": "999",  # > 850
            "ssn": "12345",  # too short
        },
    )

    assert "email" in result["updated"]
    assert "credit_score" in result["errors"]
    assert "ssn" in result["errors"]


@pytest.mark.asyncio
async def test_update_fields_auto_computes_dti(db_session, intake_seed):
    """DTI ratio is auto-computed when both income and debts are present."""
    user = borrower_sarah()
    app_id = intake_seed["active_app_id"]

    await update_application_fields(
        db_session,
        user,
        app_id,
        {"gross_monthly_income": "10000", "monthly_debts": "3000"},
    )

    db_session.expire_all()
    fin = (
        await db_session.execute(
            select(ApplicationFinancials).where(ApplicationFinancials.application_id == app_id)
        )
    ).scalar_one()
    assert fin.dti_ratio == pytest.approx(0.3, abs=0.01)


@pytest.mark.asyncio
async def test_update_fields_tracks_corrections(db_session, intake_seed):
    """Overwriting an existing value is tracked as a correction."""
    user = borrower_sarah()
    app_id = intake_seed["active_app_id"]

    # First set income
    await update_application_fields(db_session, user, app_id, {"gross_monthly_income": "5000"})
    # Correct it
    result = await update_application_fields(
        db_session, user, app_id, {"gross_monthly_income": "8000"}
    )

    assert "gross_monthly_income" in result["corrections"]
    assert result["corrections"]["gross_monthly_income"]["old"] == "5000.00"


@pytest.mark.asyncio
async def test_get_remaining_fields_empty_app(db_session, intake_seed):
    """A fresh application has all fields remaining."""
    user = borrower_sarah()
    app_id = intake_seed["active_app_id"]

    remaining = await get_remaining_fields(db_session, user, app_id)
    # The active_app has property_address and loan_amount set in seed,
    # but not loan_type, property_value, ssn, dob, employment_status, financials
    assert "loan_type" in remaining
    assert "ssn" in remaining
    assert "credit_score" in remaining
    # These were set in seed data
    assert "property_address" not in remaining
    assert "loan_amount" not in remaining


@pytest.mark.asyncio
async def test_update_fields_scope_isolation(db_session, intake_seed):
    """Michael cannot update Sarah's application."""
    user = borrower_michael()
    app_id = intake_seed["active_app_id"]

    result = await update_application_fields(db_session, user, app_id, {"loan_type": "va"})

    assert result["errors"].get("_") == "Application not found"
    assert result["updated"] == []
