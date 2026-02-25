# This project was developed with assistance from AI tools.
"""HMDA demographic data collection service.

This module is the sole permitted accessor of the hmda schema. All HMDA
reads and writes MUST go through services/compliance/ -- enforced by the
lint-hmda-isolation CI check.
"""

import json
import logging

from db import (
    Application,
    ApplicationFinancials,
    AuditEvent,
    ComplianceSessionLocal,
    HmdaDemographic,
    HmdaLoanData,
)
from db.database import SessionLocal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import UserContext
from ...schemas.hmda import HmdaCollectionRequest

logger = logging.getLogger(__name__)


async def route_extraction_demographics(
    document_id: int,
    application_id: int,
    demographic_extractions: list[dict],
) -> None:
    """Route demographic data captured during document extraction to the HMDA schema.

    Creates its own ComplianceSessionLocal -- called from background tasks
    that do not have a request-scoped session.

    Args:
        document_id: Source document ID.
        application_id: Associated application ID.
        demographic_extractions: List of dicts with field_name/field_value keys.
    """
    async with ComplianceSessionLocal() as compliance_session:
        try:
            # Map known fields to HmdaDemographic columns
            field_map: dict[str, str] = {}
            for ext in demographic_extractions:
                fname = ext.get("field_name", "").lower()
                fvalue = ext.get("field_value", "")
                if fname in ("race",):
                    field_map["race"] = fvalue
                elif fname in ("ethnicity",):
                    field_map["ethnicity"] = fvalue
                elif fname in ("sex", "gender"):
                    field_map["sex"] = fvalue
                elif fname in ("age", "age_group"):
                    field_map["age"] = fvalue

            if field_map:
                hmda_record = HmdaDemographic(
                    application_id=application_id,
                    collection_method="document_extraction",
                    **field_map,
                )
                compliance_session.add(hmda_record)

            # Log audit event for the exclusion
            event_data = json.dumps(
                {
                    "document_id": document_id,
                    "excluded_fields": [
                        {"field_name": e.get("field_name"), "field_value": e.get("field_value")}
                        for e in demographic_extractions
                    ],
                    "detection_method": "keyword_match",
                    "routed_to": "hmda.demographics",
                }
            )
            audit = AuditEvent(
                event_type="hmda_document_extraction",
                application_id=application_id,
                event_data=event_data,
            )
            compliance_session.add(audit)

            await compliance_session.commit()
        except Exception:
            logger.exception("Failed to route HMDA data for document %s", document_id)
            await compliance_session.rollback()


async def collect_demographics(
    lending_session: AsyncSession,
    compliance_session: AsyncSession,
    user: UserContext,
    request: HmdaCollectionRequest,
) -> HmdaDemographic:
    """Collect HMDA demographic data for an application.

    Args:
        lending_session: DB session using the lending_app role (public schema).
        compliance_session: DB session using the compliance_app role (hmda schema).
        user: Authenticated user context.
        request: HMDA collection request data.

    Returns:
        The created HmdaDemographic record.

    Raises:
        ValueError: If the application_id does not exist.
    """
    # Validate application exists via lending session (public schema)
    result = await lending_session.execute(
        select(Application.id).where(Application.id == request.application_id)
    )
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Application {request.application_id} not found")

    # Create demographic record via compliance session (hmda schema)
    demographic = HmdaDemographic(
        application_id=request.application_id,
        race=request.race,
        ethnicity=request.ethnicity,
        sex=request.sex,
        age=request.age,
        collection_method=request.race_collected_method,
    )
    compliance_session.add(demographic)

    # Write audit event via compliance session (audit_events is accessible)
    audit = AuditEvent(
        user_id=user.user_id,
        user_role=user.role.value,
        event_type="hmda_collection",
        application_id=request.application_id,
        event_data=json.dumps(
            {
                "race_method": request.race_collected_method,
                "ethnicity_method": request.ethnicity_collected_method,
                "sex_method": request.sex_collected_method,
            }
        ),
    )
    compliance_session.add(audit)

    await compliance_session.commit()
    await compliance_session.refresh(demographic)

    return demographic


async def snapshot_loan_data(application_id: int) -> None:
    """Snapshot non-demographic HMDA data at underwriting submission.

    Reads from lending schema (SessionLocal), writes to HMDA schema
    (ComplianceSessionLocal). Creates or updates the hmda.loan_data row.

    Args:
        application_id: The application to snapshot.
    """
    async with SessionLocal() as lending_session:
        app_result = await lending_session.execute(
            select(Application).where(Application.id == application_id)
        )
        app = app_result.scalar_one_or_none()
        if app is None:
            logger.error("Application %s not found for HMDA loan data snapshot", application_id)
            return

        fin_result = await lending_session.execute(
            select(ApplicationFinancials).where(
                ApplicationFinancials.application_id == application_id
            )
        )
        financials = fin_result.scalar_one_or_none()

    captured_fields = []
    null_fields = []

    loan_data_kwargs: dict = {"application_id": application_id}

    # From Application model
    if app.loan_type is not None:
        loan_data_kwargs["loan_type"] = (
            app.loan_type.value if hasattr(app.loan_type, "value") else str(app.loan_type)
        )
        captured_fields.append("loan_type")
    else:
        null_fields.append("loan_type")

    if app.property_address is not None:
        loan_data_kwargs["property_location"] = app.property_address
        captured_fields.append("property_location")
    else:
        null_fields.append("property_location")

    # From ApplicationFinancials model
    if financials is not None:
        for src_field, dest_field in [
            ("gross_monthly_income", "gross_monthly_income"),
            ("dti_ratio", "dti_ratio"),
            ("credit_score", "credit_score"),
        ]:
            val = getattr(financials, src_field, None)
            if val is not None:
                loan_data_kwargs[dest_field] = val
                captured_fields.append(dest_field)
            else:
                null_fields.append(dest_field)
    else:
        null_fields.extend(["gross_monthly_income", "dti_ratio", "credit_score"])

    # Fields not yet in the lending schema -- always null for now
    null_fields.extend(["loan_purpose", "interest_rate", "total_fees"])

    async with ComplianceSessionLocal() as compliance_session:
        try:
            # Upsert: check for existing row
            existing_result = await compliance_session.execute(
                select(HmdaLoanData).where(HmdaLoanData.application_id == application_id)
            )
            existing = existing_result.scalar_one_or_none()

            if existing is not None:
                for key, value in loan_data_kwargs.items():
                    if key != "application_id":
                        setattr(existing, key, value)
            else:
                compliance_session.add(HmdaLoanData(**loan_data_kwargs))

            # Audit event
            audit = AuditEvent(
                event_type="hmda_loan_data_snapshot",
                application_id=application_id,
                event_data=json.dumps(
                    {
                        "captured_fields": captured_fields,
                        "null_fields": null_fields,
                        "is_update": existing is not None,
                    }
                ),
            )
            compliance_session.add(audit)

            await compliance_session.commit()
            logger.info(
                "HMDA loan data snapshot for application %s: %d fields captured, %d null",
                application_id,
                len(captured_fields),
                len(null_fields),
            )
        except Exception:
            logger.exception("Failed to snapshot HMDA loan data for application %s", application_id)
            await compliance_session.rollback()
