# This project was developed with assistance from AI tools.
"""Rate lock status service.

Queries the rate_locks table for an application and computes the
current status (active, expired, none) with days remaining.
"""

from datetime import UTC, datetime

from db import RateLock
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.auth import UserContext
from ..services.application import get_application


async def get_rate_lock_status(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> dict | None:
    """Return rate lock status for an application.

    Applies data scope filtering so borrowers can only see their own
    applications.  Returns None if the application is not found or
    out of scope.

    Returns:
        Dict with rate lock info, or dict with status='none' if no lock exists,
        or None if application not found / out of scope.
    """
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    # Query the most recent active rate lock for this application
    lock_stmt = (
        select(RateLock)
        .where(RateLock.application_id == application_id)
        .order_by(RateLock.created_at.desc())
        .limit(1)
    )
    lock_result = await session.execute(lock_stmt)
    rate_lock = lock_result.scalar_one_or_none()

    if rate_lock is None:
        return {
            "application_id": application_id,
            "status": "none",
        }

    now = datetime.now(UTC)
    expiration = rate_lock.expiration_date
    # Ensure timezone-aware comparison
    if expiration.tzinfo is None:
        expiration = expiration.replace(tzinfo=UTC)

    days_remaining = (expiration - now).days

    if not rate_lock.is_active:
        lock_status = "expired"
    elif days_remaining < 0:
        lock_status = "expired"
    else:
        lock_status = "active"

    return {
        "application_id": application_id,
        "status": lock_status,
        "locked_rate": rate_lock.locked_rate,
        "lock_date": rate_lock.lock_date.isoformat(),
        "expiration_date": rate_lock.expiration_date.isoformat(),
        "days_remaining": max(days_remaining, 0),
        "is_urgent": 0 < days_remaining <= 7,
    }
