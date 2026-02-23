# This project was developed with assistance from AI tools.
"""Application service with role-based data scope filtering.

Every query is filtered through the caller's DataScope so that borrowers
see only their own applications, loan officers see only assigned ones,
and CEO/underwriter/admin see all.
"""

import logging

from db import Application, Borrower
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from ..schemas.auth import DataScope, UserContext

logger = logging.getLogger(__name__)


def _apply_scope(stmt, scope: DataScope, user: UserContext):
    """Apply data scope filtering to an application query."""
    if scope.own_data_only and scope.user_id:
        # Borrower: only their own applications (via borrower.keycloak_user_id)
        stmt = (
            stmt.join(Application.borrower)
            .where(Borrower.keycloak_user_id == scope.user_id)
        )
    elif scope.assigned_to:
        # Loan officer: only applications assigned to them
        stmt = stmt.where(Application.assigned_to == scope.assigned_to)
    # underwriter, admin, ceo: no filter (full_pipeline=True or default)
    return stmt


async def list_applications(
    session: AsyncSession,
    user: UserContext,
    *,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Application], int]:
    """Return applications visible to the current user."""
    # Count query
    count_stmt = select(func.count(Application.id))
    count_stmt = _apply_scope(count_stmt, user.data_scope, user)
    total = (await session.execute(count_stmt)).scalar() or 0

    # Data query
    stmt = (
        select(Application)
        .options(joinedload(Application.borrower))
        .order_by(Application.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    stmt = _apply_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    applications = result.unique().scalars().all()

    return applications, total


async def get_application(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
) -> Application | None:
    """Return a single application if visible to the current user.

    Returns None (which the route maps to 404) for out-of-scope applications
    rather than 403, to avoid leaking existence of resources.
    """
    stmt = (
        select(Application)
        .options(joinedload(Application.borrower))
        .where(Application.id == application_id)
    )
    stmt = _apply_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


async def create_application(
    session: AsyncSession,
    user: UserContext,
    loan_type=None,
    property_address: str | None = None,
    loan_amount=None,
    property_value=None,
) -> Application:
    """Create a new application for the current borrower."""
    # Find or create borrower record for the authenticated user
    stmt = select(Borrower).where(Borrower.keycloak_user_id == user.user_id)
    result = await session.execute(stmt)
    borrower = result.scalar_one_or_none()

    if borrower is None:
        borrower = Borrower(
            keycloak_user_id=user.user_id,
            first_name=user.name.split()[0] if user.name else "Unknown",
            last_name=user.name.split()[-1] if user.name and len(user.name.split()) > 1 else "",
            email=user.email,
        )
        session.add(borrower)
        await session.flush()

    application = Application(
        borrower_id=borrower.id,
        loan_type=loan_type,
        property_address=property_address,
        loan_amount=loan_amount,
        property_value=property_value,
    )
    session.add(application)
    await session.commit()
    # Re-query with joinedload to avoid lazy-load in async context
    return await get_application(session, user, application.id)


async def update_application(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    **updates,
) -> Application | None:
    """Update an application if visible to the current user."""
    app = await get_application(session, user, application_id)
    if app is None:
        return None

    for field, value in updates.items():
        if value is not None:
            setattr(app, field, value)

    await session.commit()
    # Re-query with joinedload to avoid lazy-load in async context
    return await get_application(session, user, application_id)
