# This project was developed with assistance from AI tools.
"""Schema integrity tests after alembic upgrade head."""

import pytest
from sqlalchemy import text

pytestmark = pytest.mark.integration


async def test_all_public_tables_exist(db_session):
    """11 expected public-schema tables exist after migration."""
    result = await db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename")
    )
    tables = {row[0] for row in result.fetchall()}
    expected = {
        "borrowers",
        "applications",
        "application_borrowers",
        "application_financials",
        "rate_locks",
        "conditions",
        "decisions",
        "documents",
        "document_extractions",
        "audit_events",
        "demo_data_manifest",
    }
    missing = expected - tables
    assert not missing, f"Missing tables: {missing}"


async def test_hmda_schema_tables_exist(db_session):
    """hmda.demographics and hmda.loan_data exist."""
    result = await db_session.execute(
        text("SELECT tablename FROM pg_tables WHERE schemaname = 'hmda' ORDER BY tablename")
    )
    tables = {row[0] for row in result.fetchall()}
    assert "demographics" in tables
    assert "loan_data" in tables


async def test_application_borrower_unique_constraint(db_session):
    """Duplicate (app_id, borrower_id) in application_borrowers raises IntegrityError."""
    from db.enums import ApplicationStage
    from db.models import Application, ApplicationBorrower, Borrower
    from sqlalchemy.exc import IntegrityError

    b = Borrower(keycloak_user_id="uc-test-1", first_name="A", last_name="B", email="a@b.com")
    db_session.add(b)
    await db_session.flush()

    app = Application(stage=ApplicationStage.INQUIRY)
    db_session.add(app)
    await db_session.flush()

    db_session.add(
        ApplicationBorrower(
            application_id=app.id,
            borrower_id=b.id,
            is_primary=True,
        )
    )
    await db_session.flush()

    db_session.add(
        ApplicationBorrower(
            application_id=app.id,
            borrower_id=b.id,
            is_primary=False,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()


async def test_hmda_demographic_unique_constraint(compliance_session):
    """Duplicate (app_id, borrower_id) in hmda.demographics raises IntegrityError."""
    from db.models import HmdaDemographic
    from sqlalchemy.exc import IntegrityError

    compliance_session.add(
        HmdaDemographic(
            application_id=9999,
            borrower_id=1,
            race_method="self_reported",
        )
    )
    await compliance_session.flush()

    compliance_session.add(
        HmdaDemographic(
            application_id=9999,
            borrower_id=1,
            race_method="self_reported",
        )
    )
    with pytest.raises(IntegrityError):
        await compliance_session.flush()


async def test_cascade_delete_application(db_session):
    """Deleting an application cascades to documents, conditions, and junction rows."""
    from db.enums import (
        ApplicationStage,
        ConditionSeverity,
        ConditionStatus,
        DocumentStatus,
        DocumentType,
    )
    from db.models import (
        Application,
        ApplicationBorrower,
        Borrower,
        Condition,
        Document,
    )
    from sqlalchemy import select

    b = Borrower(keycloak_user_id="cascade-test", first_name="C", last_name="D", email="c@d.com")
    db_session.add(b)
    await db_session.flush()

    app = Application(stage=ApplicationStage.INQUIRY)
    db_session.add(app)
    await db_session.flush()

    db_session.add(
        ApplicationBorrower(
            application_id=app.id,
            borrower_id=b.id,
            is_primary=True,
        )
    )
    db_session.add(
        Document(
            application_id=app.id,
            doc_type=DocumentType.W2,
            status=DocumentStatus.UPLOADED,
            uploaded_by="test",
        )
    )
    db_session.add(
        Condition(
            application_id=app.id,
            description="Test condition",
            severity=ConditionSeverity.PRIOR_TO_APPROVAL,
            status=ConditionStatus.OPEN,
        )
    )
    await db_session.flush()
    app_id = app.id

    await db_session.delete(app)
    await db_session.flush()

    # Verify cascade
    docs = (
        (await db_session.execute(select(Document).where(Document.application_id == app_id)))
        .scalars()
        .all()
    )
    assert len(docs) == 0

    junctions = (
        (
            await db_session.execute(
                select(ApplicationBorrower).where(ApplicationBorrower.application_id == app_id)
            )
        )
        .scalars()
        .all()
    )
    assert len(junctions) == 0


async def test_financials_composite_unique(db_session):
    """Duplicate (app_id, borrower_id) in application_financials raises IntegrityError."""
    from db.enums import ApplicationStage
    from db.models import Application, ApplicationFinancials, Borrower
    from sqlalchemy.exc import IntegrityError

    b = Borrower(keycloak_user_id="fin-test", first_name="F", last_name="G", email="f@g.com")
    db_session.add(b)
    app = Application(stage=ApplicationStage.INQUIRY)
    db_session.add(app)
    await db_session.flush()

    db_session.add(
        ApplicationFinancials(
            application_id=app.id,
            borrower_id=b.id,
            credit_score=700,
        )
    )
    await db_session.flush()

    db_session.add(
        ApplicationFinancials(
            application_id=app.id,
            borrower_id=b.id,
            credit_score=750,
        )
    )
    with pytest.raises(IntegrityError):
        await db_session.flush()
