# This project was developed with assistance from AI tools.
"""Disclosure acknowledgment service.

Tracks borrower acknowledgment of required lending disclosures
(Loan Estimate, privacy notice, HMDA notice, equal opportunity notice)
via the append-only audit trail.  Each acknowledgment is a separate
audit event with event_type='disclosure_acknowledged'.
"""

from db import AuditEvent
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Canonical list of disclosures a borrower must acknowledge.
REQUIRED_DISCLOSURES: list[dict[str, str]] = [
    {
        "id": "loan_estimate",
        "label": "Loan Estimate",
        "summary": (
            "The Loan Estimate provides an overview of your loan terms, "
            "projected payments, and estimated closing costs."
        ),
    },
    {
        "id": "privacy_notice",
        "label": "Privacy Notice",
        "summary": (
            "The Privacy Notice explains how Summit Cap Financial collects, "
            "uses, and protects your personal information."
        ),
    },
    {
        "id": "hmda_notice",
        "label": "HMDA Notice",
        "summary": (
            "The Home Mortgage Disclosure Act notice explains that certain "
            "demographic information is collected for federal reporting purposes "
            "and will not affect your application."
        ),
    },
    {
        "id": "equal_opportunity_notice",
        "label": "Equal Credit Opportunity Notice",
        "summary": (
            "The Equal Credit Opportunity Act prohibits discrimination in "
            "lending. This notice confirms your rights under federal law."
        ),
    },
]

_DISCLOSURE_IDS = {d["id"] for d in REQUIRED_DISCLOSURES}
_DISCLOSURE_BY_ID = {d["id"]: d for d in REQUIRED_DISCLOSURES}


async def get_disclosure_status(
    session: AsyncSession,
    application_id: int,
) -> dict:
    """Return disclosure acknowledgment status for an application.

    Queries audit_events for event_type='disclosure_acknowledged' rows
    linked to the given application_id.

    Returns:
        {
            "application_id": int,
            "all_acknowledged": bool,
            "acknowledged": ["loan_estimate", ...],
            "pending": ["privacy_notice", ...],
        }
    """
    stmt = (
        select(AuditEvent)
        .where(
            AuditEvent.event_type == "disclosure_acknowledged",
            AuditEvent.application_id == application_id,
        )
        .order_by(AuditEvent.timestamp.asc())
    )
    result = await session.execute(stmt)
    events = list(result.scalars().all())

    acknowledged_ids: set[str] = set()
    for event in events:
        if event.event_data and isinstance(event.event_data, dict):
            disc_id = event.event_data.get("disclosure_id")
            if disc_id in _DISCLOSURE_IDS:
                acknowledged_ids.add(disc_id)

    pending = [d_id for d_id in _DISCLOSURE_IDS if d_id not in acknowledged_ids]

    return {
        "application_id": application_id,
        "all_acknowledged": len(pending) == 0,
        "acknowledged": sorted(acknowledged_ids),
        "pending": sorted(pending),
    }
