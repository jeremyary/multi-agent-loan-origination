# This project was developed with assistance from AI tools.
"""Document routes with CEO content restriction (Layer 1)."""

from db import get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import CurrentUser, require_roles
from ..schemas.document import (
    DocumentDetailResponse,
    DocumentListResponse,
    DocumentResponse,
)
from ..services import document as doc_service
from ..services.document import DocumentAccessDenied

router = APIRouter()

_ALL_AUTHENTICATED = (
    UserRole.ADMIN,
    UserRole.BORROWER,
    UserRole.LOAN_OFFICER,
    UserRole.UNDERWRITER,
    UserRole.CEO,
)

_CONTENT_ROLES = (
    UserRole.ADMIN,
    UserRole.BORROWER,
    UserRole.LOAN_OFFICER,
    UserRole.UNDERWRITER,
)


@router.get(
    "/applications/{application_id}/documents",
    response_model=DocumentListResponse,
    dependencies=[Depends(require_roles(*_ALL_AUTHENTICATED))],
)
async def list_documents(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> DocumentListResponse:
    """List documents for an application. All roles see metadata only."""
    documents, total = await doc_service.list_documents(
        session,
        user,
        application_id,
        offset=offset,
        limit=limit,
    )
    items = [DocumentResponse.model_validate(doc) for doc in documents]
    return DocumentListResponse(data=items, count=total)


@router.get(
    "/documents/{document_id}",
    response_model=DocumentResponse | DocumentDetailResponse,
    dependencies=[Depends(require_roles(*_ALL_AUTHENTICATED))],
)
async def get_document(
    document_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> DocumentResponse | DocumentDetailResponse:
    """Get document metadata. CEO sees metadata only; others see file_path too."""
    doc = await doc_service.get_document(session, user, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    if user.data_scope.document_metadata_only:
        return DocumentResponse.model_validate(doc)
    return DocumentDetailResponse.model_validate(doc)


@router.get(
    "/documents/{document_id}/content",
    dependencies=[Depends(require_roles(*_CONTENT_ROLES))],
)
async def get_document_content(
    document_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> dict:
    """Get document content (file path). CEO is blocked at route level (Layer 1)."""
    doc = await doc_service.get_document(session, user, document_id)
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    try:
        file_path = doc_service.get_document_content(user, doc)
    except DocumentAccessDenied as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return {"file_path": file_path}
