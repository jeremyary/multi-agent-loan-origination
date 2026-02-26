# This project was developed with assistance from AI tools.
"""Condition service for borrower condition responses.

Handles listing open conditions (with data scope), recording text
responses, and linking uploaded documents to conditions.
"""

from db import (
    Application,
    ApplicationBorrower,
    Condition,
    ConditionStatus,
    Document,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from ..schemas.auth import UserContext
from ..services.scope import apply_data_scope


async def get_conditions(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    *,
    open_only: bool = False,
) -> list[dict] | None:
    """Return conditions for an application, respecting data scope.

    Returns None if the application is not found or out of scope.
    Returns a list of condition dicts otherwise (may be empty).
    """
    # Verify application exists and is in scope
    app_stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.id == application_id)
    )
    app_stmt = apply_data_scope(app_stmt, user.data_scope, user)
    app_result = await session.execute(app_stmt)
    app = app_result.unique().scalar_one_or_none()

    if app is None:
        return None

    # Query conditions for this application
    cond_stmt = select(Condition).where(Condition.application_id == application_id)
    if open_only:
        cond_stmt = cond_stmt.where(
            Condition.status.in_([ConditionStatus.OPEN, ConditionStatus.RESPONDED])
        )
    cond_stmt = cond_stmt.order_by(Condition.created_at)
    cond_result = await session.execute(cond_stmt)
    conditions = cond_result.scalars().all()

    return [
        {
            "id": c.id,
            "description": c.description,
            "severity": c.severity.value if c.severity else None,
            "status": c.status.value if c.status else None,
            "response_text": c.response_text,
            "issued_by": c.issued_by,
            "created_at": c.created_at.isoformat() if c.created_at else None,
        }
        for c in conditions
    ]


async def respond_to_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    response_text: str,
) -> dict | None:
    """Record a borrower's text response to a condition.

    Returns the updated condition dict, or None if not found / out of scope.
    Updates status to RESPONDED if currently OPEN.
    """
    # Verify application scope
    app_stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.id == application_id)
    )
    app_stmt = apply_data_scope(app_stmt, user.data_scope, user)
    app_result = await session.execute(app_stmt)
    app = app_result.unique().scalar_one_or_none()

    if app is None:
        return None

    # Fetch the condition
    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()

    if condition is None:
        return None

    # Record response
    condition.response_text = response_text
    if condition.status == ConditionStatus.OPEN:
        condition.status = ConditionStatus.RESPONDED

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "response_text": condition.response_text,
    }


async def link_document_to_condition(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    condition_id: int,
    document_id: int,
) -> dict | None:
    """Link a document to a condition and update status to RESPONDED.

    Returns the updated condition dict, or None if not found / out of scope.
    """
    # Verify application scope
    app_stmt = (
        select(Application)
        .options(
            selectinload(Application.application_borrowers).joinedload(ApplicationBorrower.borrower)
        )
        .where(Application.id == application_id)
    )
    app_stmt = apply_data_scope(app_stmt, user.data_scope, user)
    app_result = await session.execute(app_stmt)
    app = app_result.unique().scalar_one_or_none()

    if app is None:
        return None

    # Fetch condition
    cond_stmt = select(Condition).where(
        Condition.id == condition_id,
        Condition.application_id == application_id,
    )
    cond_result = await session.execute(cond_stmt)
    condition = cond_result.scalar_one_or_none()

    if condition is None:
        return None

    # Fetch document (must belong to the same application)
    doc_stmt = select(Document).where(
        Document.id == document_id,
        Document.application_id == application_id,
    )
    doc_result = await session.execute(doc_stmt)
    document = doc_result.scalar_one_or_none()

    if document is None:
        return None

    # Link document to condition
    document.condition_id = condition_id

    # Update condition status if OPEN
    if condition.status == ConditionStatus.OPEN:
        condition.status = ConditionStatus.RESPONDED

    await session.commit()
    await session.refresh(condition)

    return {
        "id": condition.id,
        "description": condition.description,
        "status": condition.status.value,
        "document_id": document_id,
    }
