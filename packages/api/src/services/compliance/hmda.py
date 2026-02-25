# This project was developed with assistance from AI tools.
"""HMDA demographic data collection service.

This module is the sole permitted accessor of the hmda schema. All HMDA
reads and writes MUST go through services/compliance/ -- enforced by the
lint-hmda-isolation CI check.
"""

import logging

from db import (
    Application,
    ApplicationBorrower,
    ApplicationFinancials,
    AuditEvent,
    ComplianceSessionLocal,
    HmdaDemographic,
    HmdaLoanData,
)
from db.database import SessionLocal
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import UserContext
from ...schemas.hmda import HmdaCollectionRequest
from ...services.scope import apply_data_scope

logger = logging.getLogger(__name__)

# Higher value = higher precedence. self_reported always wins over document_extraction.
_METHOD_PRECEDENCE = {"self_reported": 2, "document_extraction": 1}

_DEMOGRAPHIC_FIELDS = ("race", "ethnicity", "sex", "age")


async def _upsert_demographics(
    compliance_session: AsyncSession,
    application_id: int,
    borrower_id: int | None,
    fields: dict,
    methods: dict[str, str],
) -> tuple[HmdaDemographic, list[dict]]:
    """Upsert a demographics row for (application_id, borrower_id).

    If no existing row, inserts a new one. If existing row found, compares
    each field and applies per-field precedence rules:
    - Incoming is None -> skip (don't overwrite with nothing)
    - Existing is None -> fill in (no conflict)
    - Values match -> skip
    - Values differ -> conflict: higher-precedence method wins (per-field)

    Args:
        fields: Dict of demographic field values (race, ethnicity, sex, age).
        methods: Dict of per-field collection methods (race, ethnicity, sex, age).

    Returns:
        (demographic_record, conflicts_list)
    """
    # Query existing row by (application_id, borrower_id)
    stmt = select(HmdaDemographic).where(
        and_(
            HmdaDemographic.application_id == application_id,
            HmdaDemographic.borrower_id == borrower_id
            if borrower_id is not None
            else HmdaDemographic.borrower_id.is_(None),
        )
    )
    result = await compliance_session.execute(stmt)
    existing = result.scalar_one_or_none()

    if existing is None:
        # No existing row -- simple INSERT with per-field methods
        method_kwargs = {
            f"{k}_method": methods.get(k, "self_reported")
            for k in _DEMOGRAPHIC_FIELDS
            if fields.get(k) is not None
        }
        record = HmdaDemographic(
            application_id=application_id,
            borrower_id=borrower_id,
            **{k: v for k, v in fields.items() if k in _DEMOGRAPHIC_FIELDS},
            **method_kwargs,
        )
        compliance_session.add(record)
        return record, []

    # Existing row -- compare fields and apply per-field precedence
    conflicts = []

    for field_name in _DEMOGRAPHIC_FIELDS:
        incoming_val = fields.get(field_name)
        if incoming_val is None:
            continue

        incoming_method = methods.get(field_name, "self_reported")
        existing_method = getattr(existing, f"{field_name}_method", None)
        incoming_prec = _METHOD_PRECEDENCE.get(incoming_method, 0)
        existing_prec = _METHOD_PRECEDENCE.get(existing_method, 0)

        existing_val = getattr(existing, field_name, None)
        if existing_val is None:
            # Fill gap -- no conflict
            setattr(existing, field_name, incoming_val)
            setattr(existing, f"{field_name}_method", incoming_method)
            continue

        if existing_val == incoming_val:
            continue

        # Values differ -- conflict resolved per-field
        if incoming_prec >= existing_prec:
            setattr(existing, field_name, incoming_val)
            setattr(existing, f"{field_name}_method", incoming_method)
            conflicts.append(
                {
                    "field": field_name,
                    "old_value": existing_val,
                    "new_value": incoming_val,
                    "resolution": "overwritten",
                    "reason": f"{incoming_method} >= {existing_method}",
                }
            )
        else:
            conflicts.append(
                {
                    "field": field_name,
                    "old_value": existing_val,
                    "new_value": incoming_val,
                    "resolution": "kept_existing",
                    "reason": f"{existing_method} > {incoming_method}",
                }
            )

    return existing, conflicts


async def route_extraction_demographics(
    document_id: int,
    application_id: int,
    demographic_extractions: list[dict],
    *,
    borrower_id: int | None = None,
) -> None:
    """Route demographic data captured during document extraction to the HMDA schema.

    Creates its own ComplianceSessionLocal -- called from background tasks
    that do not have a request-scoped session.

    Args:
        document_id: Source document ID.
        application_id: Associated application ID.
        demographic_extractions: List of dicts with field_name/field_value keys.
        borrower_id: Optional borrower ID from the document.
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

            conflicts = []
            if field_map:
                # Build per-field methods dict: all fields from extraction use document_extraction
                extraction_methods = {k: "document_extraction" for k in field_map}
                _, conflicts = await _upsert_demographics(
                    compliance_session,
                    application_id,
                    borrower_id,
                    field_map,
                    extraction_methods,
                )

            # Log audit event for the exclusion
            event_data = {
                "document_id": document_id,
                "borrower_id": borrower_id,
                "excluded_fields": [
                    {"field_name": e.get("field_name"), "field_value": e.get("field_value")}
                    for e in demographic_extractions
                ],
                "detection_method": "keyword_match",
                "routed_to": "hmda.demographics",
                "conflicts": conflicts,
            }
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
) -> tuple[HmdaDemographic, list[dict]]:
    """Collect HMDA demographic data for an application.

    Args:
        lending_session: DB session using the lending_app role (public schema).
        compliance_session: DB session using the compliance_app role (hmda schema).
        user: Authenticated user context.
        request: HMDA collection request data.

    Returns:
        Tuple of (HmdaDemographic record, conflicts list).

    Raises:
        ValueError: If the application_id does not exist.
    """
    # Validate application exists and caller has access (D9: scoped ownership check)
    scope_stmt = select(Application.id).where(Application.id == request.application_id)
    scope_stmt = apply_data_scope(scope_stmt, user.data_scope, user)
    result = await lending_session.execute(scope_stmt)
    if result.scalar_one_or_none() is None:
        raise ValueError(f"Application {request.application_id} not found")

    # Validate borrower_id belongs to application when explicitly provided (D19)
    borrower_id = request.borrower_id
    if borrower_id is not None:
        valid_stmt = select(ApplicationBorrower.borrower_id).where(
            ApplicationBorrower.application_id == request.application_id,
            ApplicationBorrower.borrower_id == borrower_id,
        )
        valid_result = await lending_session.execute(valid_stmt)
        if valid_result.scalar_one_or_none() is None:
            raise ValueError(
                f"Borrower {borrower_id} is not linked to application {request.application_id}"
            )
    if borrower_id is None:
        primary_stmt = select(ApplicationBorrower.borrower_id).where(
            ApplicationBorrower.application_id == request.application_id,
            ApplicationBorrower.is_primary.is_(True),
        )
        primary_result = await lending_session.execute(primary_stmt)
        borrower_id = primary_result.scalar_one_or_none()

    # Upsert demographic record via compliance session (hmda schema)
    fields = {
        "race": request.race,
        "ethnicity": request.ethnicity,
        "sex": request.sex,
        "age": request.age,
    }
    methods = {
        "race": request.race_collected_method,
        "ethnicity": request.ethnicity_collected_method,
        "sex": request.sex_collected_method,
        "age": request.age_collected_method,
    }
    demographic, conflicts = await _upsert_demographics(
        compliance_session,
        request.application_id,
        borrower_id,
        fields,
        methods,
    )

    # Write audit event via compliance session (audit_events is accessible)
    audit = AuditEvent(
        user_id=user.user_id,
        user_role=user.role.value,
        event_type="hmda_collection",
        application_id=request.application_id,
        event_data={
            "borrower_id": borrower_id,
            "race_method": request.race_collected_method,
            "ethnicity_method": request.ethnicity_collected_method,
            "sex_method": request.sex_collected_method,
            "age_method": request.age_collected_method,
            "conflicts": conflicts,
        },
    )
    compliance_session.add(audit)

    await compliance_session.commit()
    await compliance_session.refresh(demographic)

    return demographic, conflicts


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
                event_data={
                    "captured_fields": captured_fields,
                    "null_fields": null_fields,
                    "is_update": existing is not None,
                },
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
