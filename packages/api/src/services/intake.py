# This project was developed with assistance from AI tools.
"""Application intake service for conversational data collection.

Handles the lifecycle of mortgage application intake: finding active
applications, creating new ones, and tracking collection progress.
"""

import logging

from db import Application, ApplicationBorrower
from db.enums import ApplicationStage
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..schemas.auth import UserContext
from ..services.application import create_application
from ..services.scope import apply_data_scope

logger = logging.getLogger(__name__)

# Terminal stages -- applications in these stages are not considered "active"
_TERMINAL_STAGES = {
    ApplicationStage.WITHDRAWN,
    ApplicationStage.DENIED,
    ApplicationStage.CLOSED,
}


async def find_active_application(
    session: AsyncSession,
    user: UserContext,
) -> Application | None:
    """Find the user's most recent non-terminal application.

    Returns None if the user has no active applications. Withdrawn, denied,
    and closed applications are excluded.
    """
    stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.stage.notin_([s.value for s in _TERMINAL_STAGES]))
        .order_by(Application.updated_at.desc())
        .limit(1)
    )
    stmt = apply_data_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def start_application(
    session: AsyncSession,
    user: UserContext,
) -> dict:
    """Start a new application or return an existing active one.

    Returns a dict with:
        - application_id: The application ID
        - stage: Current stage
        - is_new: True if a new application was created
    """
    existing = await find_active_application(session, user)
    if existing is not None:
        return {
            "application_id": existing.id,
            "stage": existing.stage.value
            if isinstance(existing.stage, ApplicationStage)
            else existing.stage,
            "is_new": False,
        }

    app = await create_application(session, user)
    return {
        "application_id": app.id,
        "stage": app.stage.value if isinstance(app.stage, ApplicationStage) else app.stage,
        "is_new": True,
    }
