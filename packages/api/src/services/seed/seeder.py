# This project was developed with assistance from AI tools.
"""Demo data seeding service.

Seeds the database with realistic mortgage applications, borrowers,
documents, conditions, decisions, rate locks, and HMDA demographics
so all 5 personas have data to explore immediately after deployment.

Simulated for demonstration purposes -- not real financial data.
"""

import json
import logging
from datetime import UTC, datetime

from db import (
    Application,
    ApplicationFinancials,
    AuditEvent,
    Borrower,
    Condition,
    Decision,
    DemoDataManifest,
    Document,
    RateLock,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..compliance.seed_hmda import clear_hmda_demographics, seed_hmda_demographics
from .fixtures import (
    ACTIVE_APPLICATIONS,
    BORROWERS,
    HISTORICAL_LOANS,
    HMDA_DEMOGRAPHICS,
    compute_config_hash,
)

logger = logging.getLogger(__name__)


async def _check_manifest(session: AsyncSession) -> DemoDataManifest | None:
    """Check if demo data has been seeded."""
    result = await session.execute(
        select(DemoDataManifest).order_by(DemoDataManifest.id.desc()).limit(1)
    )
    return result.scalar_one_or_none()


async def _clear_demo_data(session: AsyncSession, compliance_session: AsyncSession) -> None:
    """Delete all demo data by known borrower keycloak IDs."""
    known_ids = [b["keycloak_user_id"] for b in BORROWERS]

    # Find borrower rows to get their IDs for cascade
    result = await session.execute(
        select(Borrower.id).where(Borrower.keycloak_user_id.in_(known_ids))
    )
    borrower_ids = list(result.scalars().all())

    if borrower_ids:
        # Find application IDs linked to these borrowers
        app_result = await session.execute(
            select(Application.id).where(Application.borrower_id.in_(borrower_ids))
        )
        app_ids = list(app_result.scalars().all())

        if app_ids:
            # Delete child records first (no FK cascade assumed)
            await session.execute(delete(Document).where(Document.application_id.in_(app_ids)))
            await session.execute(delete(Condition).where(Condition.application_id.in_(app_ids)))
            await session.execute(delete(Decision).where(Decision.application_id.in_(app_ids)))
            await session.execute(delete(RateLock).where(RateLock.application_id.in_(app_ids)))
            await session.execute(
                delete(ApplicationFinancials).where(
                    ApplicationFinancials.application_id.in_(app_ids)
                )
            )
            # Delete audit events for these applications
            await session.execute(delete(AuditEvent).where(AuditEvent.application_id.in_(app_ids)))
            # Delete HMDA demographics via compliance module (isolation boundary)
            await clear_hmda_demographics(compliance_session, app_ids)
            # Delete applications
            await session.execute(delete(Application).where(Application.id.in_(app_ids)))

        # Delete borrowers
        await session.execute(delete(Borrower).where(Borrower.id.in_(borrower_ids)))

    # Delete seed-related audit events
    await session.execute(delete(AuditEvent).where(AuditEvent.event_type == "demo_data_seeded"))

    # Clear manifest
    await session.execute(delete(DemoDataManifest))

    logger.info("Cleared existing demo data")


def _create_borrower_map(borrowers: list[Borrower]) -> dict[str, int]:
    """Map keycloak_user_id -> borrower.id for FK resolution."""
    return {b.keycloak_user_id: b.id for b in borrowers}


async def _seed_applications(
    session: AsyncSession,
    app_defs: list[dict],
    borrower_map: dict[str, int],
) -> list[Application]:
    """Seed application records with financials, documents, conditions, decisions, rate locks."""
    applications = []

    for app_def in app_defs:
        borrower_id = borrower_map[app_def["borrower_ref"]]

        app = Application(
            borrower_id=borrower_id,
            stage=app_def["stage"],
            loan_type=app_def["loan_type"],
            property_address=app_def["property_address"],
            loan_amount=app_def["loan_amount"],
            property_value=app_def["property_value"],
            assigned_to=app_def["assigned_to"],
        )
        session.add(app)
        await session.flush()  # Get app.id

        # Financials
        fin_data = app_def["financials"]
        financials = ApplicationFinancials(
            application_id=app.id,
            gross_monthly_income=fin_data["gross_monthly_income"],
            monthly_debts=fin_data["monthly_debts"],
            total_assets=fin_data["total_assets"],
            credit_score=fin_data["credit_score"],
            dti_ratio=fin_data["dti_ratio"],
        )
        session.add(financials)

        # Documents
        for doc_def in app_def.get("documents", []):
            doc = Document(
                application_id=app.id,
                doc_type=doc_def["doc_type"],
                status=doc_def["status"],
                file_path=f"/demo/docs/{app.id}/{doc_def['doc_type'].value}.pdf",
                quality_flags=doc_def.get("quality_flags"),
                uploaded_by=app_def["borrower_ref"],
            )
            session.add(doc)

        # Conditions
        for cond_def in app_def.get("conditions", []):
            condition = Condition(
                application_id=app.id,
                description=cond_def["description"],
                severity=cond_def["severity"],
                status=cond_def["status"],
                issued_by=cond_def.get("issued_by"),
                cleared_by=cond_def.get("cleared_by"),
            )
            session.add(condition)

        # Decisions
        for dec_def in app_def.get("decisions", []):
            decision = Decision(
                application_id=app.id,
                decision_type=dec_def["decision_type"],
                rationale=dec_def["rationale"],
                decided_by=dec_def.get("decided_by"),
            )
            session.add(decision)

        # Rate lock
        if "rate_lock" in app_def:
            rl_def = app_def["rate_lock"]
            rate_lock = RateLock(
                application_id=app.id,
                locked_rate=rl_def["locked_rate"],
                lock_date=rl_def["lock_date"],
                expiration_date=rl_def["expiration_date"],
                is_active=rl_def["is_active"],
            )
            session.add(rate_lock)

        # Audit event for application creation
        audit = AuditEvent(
            user_id=app_def["assigned_to"],
            user_role="system",
            event_type="application_created",
            application_id=app.id,
            event_data=json.dumps({"source": "demo_seed", "stage": app_def["stage"].value}),
        )
        session.add(audit)

        applications.append(app)

    return applications


async def seed_demo_data(
    session: AsyncSession,
    compliance_session: AsyncSession,
    force: bool = False,
) -> dict:
    """Seed demo data. Returns summary dict.

    Args:
        session: Main lending DB session.
        compliance_session: HMDA compliance DB session.
        force: If True, clear and re-seed even if already seeded.

    Returns:
        Summary dict with counts of seeded records.

    Raises:
        RuntimeError: If already seeded and force=False.
    """
    manifest = await _check_manifest(session)
    if manifest and not force:
        return {
            "status": "already_seeded",
            "seeded_at": manifest.seeded_at.isoformat(),
            "config_hash": manifest.config_hash,
        }

    if manifest and force:
        await _clear_demo_data(session, compliance_session)

    # 1. Create borrowers
    borrower_records = []
    for b_data in BORROWERS:
        borrower = Borrower(
            keycloak_user_id=b_data["keycloak_user_id"],
            first_name=b_data["first_name"],
            last_name=b_data["last_name"],
            email=b_data["email"],
            ssn_encrypted=b_data.get("ssn_encrypted"),
            dob=b_data.get("dob"),
        )
        session.add(borrower)
        borrower_records.append(borrower)

    await session.flush()  # Get borrower IDs
    borrower_map = _create_borrower_map(borrower_records)

    # 2. Seed active applications
    active_apps = await _seed_applications(session, ACTIVE_APPLICATIONS, borrower_map)

    # 3. Seed historical loans
    historical_apps = await _seed_applications(session, HISTORICAL_LOANS, borrower_map)

    all_apps = active_apps + historical_apps

    # 4. Seed HMDA demographics via compliance session
    hmda_records = []
    for i, demo_data in enumerate(HMDA_DEMOGRAPHICS):
        if i < len(all_apps):
            hmda_records.append(
                {
                    "application_id": all_apps[i].id,
                    "race": demo_data["race"],
                    "ethnicity": demo_data["ethnicity"],
                    "sex": demo_data["sex"],
                    "collection_method": demo_data["collection_method"],
                }
            )

    hmda_count = await seed_hmda_demographics(compliance_session, hmda_records)

    # 5. Write manifest
    config_hash = compute_config_hash()
    summary = {
        "borrowers": len(borrower_records),
        "active_applications": len(active_apps),
        "historical_loans": len(historical_apps),
        "hmda_demographics": hmda_count,
    }

    manifest = DemoDataManifest(
        config_hash=config_hash,
        summary=json.dumps(summary),
    )
    session.add(manifest)

    # Seed-level audit event
    audit = AuditEvent(
        user_id="system",
        user_role="system",
        event_type="demo_data_seeded",
        event_data=json.dumps(summary),
    )
    session.add(audit)

    # 6. Commit both sessions
    await session.commit()
    await compliance_session.commit()

    logger.info("Demo data seeded: %s", summary)

    return {
        "status": "seeded",
        "seeded_at": datetime.now(UTC).isoformat(),
        "config_hash": config_hash,
        **summary,
    }


async def get_seed_status(session: AsyncSession) -> dict:
    """Check if demo data has been seeded."""
    manifest = await _check_manifest(session)
    if manifest is None:
        return {"seeded": False}
    return {
        "seeded": True,
        "seeded_at": manifest.seeded_at.isoformat(),
        "config_hash": manifest.config_hash,
        "summary": json.loads(manifest.summary) if manifest.summary else None,
    }
