# This project was developed with assistance from AI tools.
"""Application CRUD routes with RBAC enforcement."""

from db import get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import CurrentUser, require_roles
from ..middleware.pii import mask_application_pii
from ..schemas.application import (
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
)
from ..services import application as app_service

router = APIRouter()


@router.get(
    "/",
    response_model=ApplicationListResponse,
    dependencies=[Depends(require_roles(
        UserRole.ADMIN, UserRole.BORROWER, UserRole.LOAN_OFFICER,
        UserRole.UNDERWRITER, UserRole.CEO,
    ))],
)
async def list_applications(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
):
    """List applications visible to the current user's role and data scope."""
    applications, total = await app_service.list_applications(
        session, user, offset=offset, limit=limit,
    )
    items = [
        ApplicationResponse.model_validate(app) for app in applications
    ]
    if user.data_scope.pii_mask:
        items = [
            ApplicationResponse.model_validate(mask_application_pii(item.model_dump()))
            for item in items
        ]
    return ApplicationListResponse(data=items, count=total)


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    dependencies=[Depends(require_roles(
        UserRole.ADMIN, UserRole.BORROWER, UserRole.LOAN_OFFICER,
        UserRole.UNDERWRITER, UserRole.CEO,
    ))],
)
async def get_application(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Get a single application. Returns 404 for out-of-scope resources."""
    app = await app_service.get_application(session, user, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    item = ApplicationResponse.model_validate(app)
    if user.data_scope.pii_mask:
        item = ApplicationResponse.model_validate(
            mask_application_pii(item.model_dump())
        )
    return item


@router.post(
    "/",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.BORROWER, UserRole.ADMIN))],
)
async def create_application(
    body: ApplicationCreate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Create a new application. Borrowers and admins only."""
    app = await app_service.create_application(
        session,
        user,
        loan_type=body.loan_type,
        property_address=body.property_address,
        loan_amount=body.loan_amount,
        property_value=body.property_value,
    )
    return ApplicationResponse.model_validate(app)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    dependencies=[Depends(require_roles(
        UserRole.ADMIN, UserRole.LOAN_OFFICER, UserRole.UNDERWRITER,
    ))],
)
async def update_application(
    application_id: int,
    body: ApplicationUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Update an application. LOs, underwriters, and admins only."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )
    app = await app_service.update_application(
        session, user, application_id, **updates,
    )
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ApplicationResponse.model_validate(app)
