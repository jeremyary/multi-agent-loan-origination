# This project was developed with assistance from AI tools.
"""Urgency calculation service for loan officer pipeline management.

Batch-computes urgency indicators for applications based on rate lock
expiry, stage timing, open conditions, and document request age.
"""

import logging
from datetime import UTC, datetime

from db import Application, Condition, Document, RateLock
from db.enums import ApplicationStage, ConditionStatus, DocumentStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.urgency import UrgencyIndicator, UrgencyLevel

logger = logging.getLogger(__name__)

# Expected days per stage (MVP hardcoded defaults)
EXPECTED_STAGE_DAYS: dict[ApplicationStage, int] = {
    ApplicationStage.INQUIRY: 3,
    ApplicationStage.PREQUALIFICATION: 5,
    ApplicationStage.APPLICATION: 7,
    ApplicationStage.PROCESSING: 5,
    ApplicationStage.UNDERWRITING: 5,
    ApplicationStage.CONDITIONAL_APPROVAL: 10,
    ApplicationStage.CLEAR_TO_CLOSE: 7,
}

# Condition statuses that count as resolved
_RESOLVED_STATUSES = {ConditionStatus.CLEARED, ConditionStatus.WAIVED}

# Document statuses that represent a pending request (uploaded but not yet reviewed)
_PENDING_DOC_STATUSES = {
    DocumentStatus.UPLOADED,
    DocumentStatus.PROCESSING,
    DocumentStatus.PENDING_REVIEW,
}


async def compute_urgency(
    session: AsyncSession,
    applications: list[Application],
    *,
    now: datetime | None = None,
) -> dict[int, UrgencyIndicator]:
    """Batch-compute urgency for multiple applications.

    Args:
        session: Database session.
        applications: List of Application ORM objects (must have id, stage,
            updated_at already loaded).
        now: Override current time (for testing).

    Returns:
        Mapping of application_id to UrgencyIndicator.
    """
    if not applications:
        return {}

    if now is None:
        now = datetime.now(UTC)

    app_ids = [app.id for app in applications]

    # Batch queries
    rate_locks = await _batch_active_rate_locks(session, app_ids)
    open_condition_counts = await _batch_open_condition_counts(session, app_ids)
    oldest_pending_docs = await _batch_oldest_pending_docs(session, app_ids)

    result: dict[int, UrgencyIndicator] = {}
    for app in applications:
        factors: list[str] = []
        levels: list[UrgencyLevel] = []

        # Factor 1: Rate lock expiry
        lock = rate_locks.get(app.id)
        if lock:
            _assess_rate_lock(lock, now, levels, factors)

        # Factor 2: Stage timing
        stage = app.stage or ApplicationStage.INQUIRY
        expected = EXPECTED_STAGE_DAYS.get(stage)
        updated_at = _ensure_tz(app.updated_at)
        days_in_stage = max((now - updated_at).days, 0)

        if expected:
            _assess_stage_timing(days_in_stage, expected, stage, levels, factors)
        else:
            expected = 0

        # Factor 3: Open conditions
        open_count = open_condition_counts.get(app.id, 0)
        if open_count > 0 and lock:
            _assess_conditions_with_lock(open_count, lock, now, levels, factors)

        # Factor 4: Pending document age
        oldest_doc_created = oldest_pending_docs.get(app.id)
        if oldest_doc_created:
            _assess_pending_docs(oldest_doc_created, now, levels, factors)

        level = min(levels) if levels else UrgencyLevel.NORMAL

        result[app.id] = UrgencyIndicator(
            level=level,
            factors=factors,
            days_in_stage=days_in_stage,
            expected_stage_days=expected or 0,
        )

    return result


def _ensure_tz(dt: datetime) -> datetime:
    """Ensure a datetime is timezone-aware (UTC)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _assess_rate_lock(
    lock: RateLock,
    now: datetime,
    levels: list[UrgencyLevel],
    factors: list[str],
) -> None:
    """Assess urgency from rate lock expiry."""
    expiration = _ensure_tz(lock.expiration_date)
    days_remaining = (expiration - now).days

    if days_remaining <= 3:
        levels.append(UrgencyLevel.CRITICAL)
        factors.append(f"Rate lock expires in {max(days_remaining, 0)} days")
    elif days_remaining <= 7:
        levels.append(UrgencyLevel.HIGH)
        factors.append(f"Rate lock expires in {days_remaining} days")


def _assess_stage_timing(
    days_in_stage: int,
    expected: int,
    stage: ApplicationStage,
    levels: list[UrgencyLevel],
    factors: list[str],
) -> None:
    """Assess urgency from time in current stage."""
    overdue = days_in_stage - expected
    label = stage.value.replace("_", " ").title()

    if overdue >= 7:
        levels.append(UrgencyLevel.CRITICAL)
        factors.append(f"{label} stage overdue by {overdue} days")
    elif overdue >= 4:
        levels.append(UrgencyLevel.HIGH)
        factors.append(f"{label} stage overdue by {overdue} days")
    elif days_in_stage >= int(expected * 0.8):
        levels.append(UrgencyLevel.MEDIUM)
        factors.append(f"{label} stage at {days_in_stage}/{expected} expected days")


def _assess_conditions_with_lock(
    open_count: int,
    lock: RateLock,
    now: datetime,
    levels: list[UrgencyLevel],
    factors: list[str],
) -> None:
    """Assess urgency from open conditions combined with rate lock deadline."""
    expiration = _ensure_tz(lock.expiration_date)
    days_remaining = (expiration - now).days

    if open_count > 0 and days_remaining <= 5:
        levels.append(UrgencyLevel.CRITICAL)
        factors.append(
            f"{open_count} open condition(s) with rate lock expiring in "
            f"{max(days_remaining, 0)} days"
        )


def _assess_pending_docs(
    oldest_created: datetime,
    now: datetime,
    levels: list[UrgencyLevel],
    factors: list[str],
) -> None:
    """Assess urgency from age of pending document requests."""
    oldest_created = _ensure_tz(oldest_created)
    hours_pending = (now - oldest_created).total_seconds() / 3600

    if hours_pending >= 48:
        levels.append(UrgencyLevel.HIGH)
        factors.append(f"Document request pending for {int(hours_pending)} hours")


# ---------------------------------------------------------------------------
# Batch query helpers
# ---------------------------------------------------------------------------


async def _batch_active_rate_locks(
    session: AsyncSession,
    app_ids: list[int],
) -> dict[int, RateLock]:
    """Return the most recent active rate lock per application."""
    stmt = (
        select(RateLock)
        .where(
            RateLock.application_id.in_(app_ids),
            RateLock.is_active.is_(True),
        )
        .order_by(RateLock.created_at.desc())
    )
    result = await session.execute(stmt)
    locks = result.scalars().all()

    # Keep only the most recent per app
    by_app: dict[int, RateLock] = {}
    for lock in locks:
        if lock.application_id not in by_app:
            by_app[lock.application_id] = lock
    return by_app


async def _batch_open_condition_counts(
    session: AsyncSession,
    app_ids: list[int],
) -> dict[int, int]:
    """Return count of open (unresolved) conditions per application."""
    stmt = (
        select(
            Condition.application_id,
            func.count().label("cnt"),
        )
        .where(
            Condition.application_id.in_(app_ids),
            Condition.status.notin_([s.value for s in _RESOLVED_STATUSES]),
        )
        .group_by(Condition.application_id)
    )
    result = await session.execute(stmt)
    return {row.application_id: row.cnt for row in result}


async def _batch_oldest_pending_docs(
    session: AsyncSession,
    app_ids: list[int],
) -> dict[int, datetime]:
    """Return the oldest pending document created_at per application."""
    stmt = (
        select(
            Document.application_id,
            func.min(Document.created_at).label("oldest"),
        )
        .where(
            Document.application_id.in_(app_ids),
            Document.status.in_([s.value for s in _PENDING_DOC_STATUSES]),
        )
        .group_by(Document.application_id)
    )
    result = await session.execute(stmt)
    return {row.application_id: row.oldest for row in result}
