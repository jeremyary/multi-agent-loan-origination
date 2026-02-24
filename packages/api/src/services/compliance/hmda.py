# This project was developed with assistance from AI tools.
"""HMDA demographic data collection service.

This module is the sole permitted accessor of the hmda schema. All HMDA
reads and writes MUST go through services/compliance/ -- enforced by the
lint-hmda-isolation CI check.
"""

import json
import logging

from db import Application, AuditEvent, HmdaDemographic
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ...schemas.auth import UserContext
from ...schemas.hmda import HmdaCollectionRequest

logger = logging.getLogger(__name__)


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
