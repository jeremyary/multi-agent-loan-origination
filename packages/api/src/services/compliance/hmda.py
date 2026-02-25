# This project was developed with assistance from AI tools.
"""HMDA demographic data collection service.

This module is the sole permitted accessor of the hmda schema. All HMDA
reads and writes MUST go through services/compliance/ -- enforced by the
lint-hmda-isolation CI check.
"""

import json
import logging

from db import Application, AuditEvent, ComplianceSessionLocal, HmdaDemographic
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
