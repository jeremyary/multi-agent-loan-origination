# This project was developed with assistance from AI tools.
"""HMDA demographic seeding -- lives inside services/compliance/ for isolation."""

import logging

from db import HmdaDemographic
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def clear_hmda_demographics(
    compliance_session: AsyncSession,
    application_ids: list[int],
) -> None:
    """Delete HMDA demographics for the given application IDs."""
    if application_ids:
        await compliance_session.execute(
            delete(HmdaDemographic).where(HmdaDemographic.application_id.in_(application_ids))
        )
        logger.info("Cleared HMDA demographics for %d applications", len(application_ids))


async def seed_hmda_demographics(
    compliance_session: AsyncSession,
    application_demographics: list[dict],
) -> int:
    """Seed HMDA demographics for applications.

    Args:
        compliance_session: DB session using the compliance_app role (hmda schema).
        application_demographics: List of dicts with keys: application_id, race,
            ethnicity, sex, collection_method.

    Returns:
        Number of demographic records created.
    """
    count = 0
    for demo_data in application_demographics:
        demographic = HmdaDemographic(
            application_id=demo_data["application_id"],
            race=demo_data["race"],
            ethnicity=demo_data["ethnicity"],
            sex=demo_data["sex"],
            collection_method=demo_data["collection_method"],
        )
        compliance_session.add(demographic)
        count += 1

    logger.info("Seeded %d HMDA demographic records", count)
    return count
