# This project was developed with assistance from AI tools.
"""Document service with content restriction for metadata-only scopes.

Roles with document_metadata_only scope see document metadata only --
file_path and content are stripped at the service layer (defense-in-depth
Layer 2). The route layer provides Layer 1, and the response schema
provides Layer 4.
"""

import logging

from db import Application, Borrower, Document
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..schemas.auth import DataScope, UserContext

logger = logging.getLogger(__name__)


class DocumentAccessDenied(Exception):
    """Raised when a role is not allowed to access document content."""


def _apply_scope(stmt, scope: DataScope, user: UserContext):
    """Apply data scope filtering to a document query via its application."""
    if scope.own_data_only and scope.user_id:
        stmt = (
            stmt.join(Document.application)
            .join(Application.borrower)
            .where(Borrower.keycloak_user_id == scope.user_id)
        )
    elif scope.assigned_to:
        stmt = stmt.join(Document.application).where(Application.assigned_to == scope.assigned_to)
    return stmt


async def list_documents(
    session: AsyncSession,
    user: UserContext,
    application_id: int,
    *,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Document], int]:
    """Return documents for an application visible to the current user."""
    count_stmt = select(func.count(Document.id)).where(Document.application_id == application_id)
    count_stmt = _apply_scope(count_stmt, user.data_scope, user)
    total = (await session.execute(count_stmt)).scalar() or 0

    stmt = (
        select(Document)
        .where(Document.application_id == application_id)
        .order_by(Document.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    stmt = _apply_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    documents = result.unique().scalars().all()

    return documents, total


async def get_document(
    session: AsyncSession,
    user: UserContext,
    document_id: int,
) -> Document | None:
    """Return a single document if visible to the current user."""
    stmt = select(Document).where(Document.id == document_id)
    stmt = _apply_scope(stmt, user.data_scope, user)
    result = await session.execute(stmt)
    return result.unique().scalar_one_or_none()


def get_document_content(user: UserContext, document: Document) -> str | None:
    """Return document file_path, enforcing content restriction.

    Raises DocumentAccessDenied for metadata-only scopes (service-level
    enforcement, defense-in-depth Layer 2).
    """
    if user.data_scope.document_metadata_only:
        raise DocumentAccessDenied("Document content access denied (metadata-only scope)")
    return document.file_path
