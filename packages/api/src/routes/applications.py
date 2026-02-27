# This project was developed with assistance from AI tools.
"""Application CRUD routes with RBAC enforcement."""

from typing import Literal

from db import Application, ApplicationBorrower, Borrower, get_db
from db.enums import ApplicationStage, UserRole
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import CurrentUser, require_roles
from ..schemas import Pagination
from ..schemas.application import (
    AddBorrowerRequest,
    ApplicationCreate,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdate,
    BorrowerSummary,
)
from ..schemas.condition import (
    ConditionItem,
    ConditionListResponse,
    ConditionRespondRequest,
    ConditionResponse,
)
from ..schemas.rate_lock import RateLockResponse
from ..schemas.status import ApplicationStatusResponse
from ..schemas.urgency import UrgencyLevel
from ..services import application as app_service
from ..services.condition import get_conditions, respond_to_condition
from ..services.rate_lock import get_rate_lock_status
from ..services.status import get_application_status
from ..services.urgency import compute_urgency

router = APIRouter()


def _build_app_response(app: Application) -> ApplicationResponse:
    """Build ApplicationResponse from ORM object, populating borrowers list.

    The ``urgency`` field is schema-only (not an ORM column) and is set to
    None here. The route layer populates it after batch computation.
    """
    borrowers = []
    for ab in getattr(app, "application_borrowers", []) or []:
        if ab.borrower:
            borrowers.append(
                BorrowerSummary(
                    id=ab.borrower.id,
                    first_name=ab.borrower.first_name,
                    last_name=ab.borrower.last_name,
                    email=ab.borrower.email,
                    ssn=ab.borrower.ssn,
                    dob=ab.borrower.dob,
                    employment_status=ab.borrower.employment_status,
                    is_primary=ab.is_primary,
                )
            )

    return ApplicationResponse(
        id=app.id,
        stage=app.stage,
        loan_type=app.loan_type,
        property_address=app.property_address,
        loan_amount=app.loan_amount,
        property_value=app.property_value,
        assigned_to=app.assigned_to,
        created_at=app.created_at,
        updated_at=app.updated_at,
        borrowers=borrowers,
    )


_URGENCY_ROLES = {UserRole.LOAN_OFFICER, UserRole.ADMIN}

_URGENCY_ORDER = {
    UrgencyLevel.CRITICAL: 0,
    UrgencyLevel.HIGH: 1,
    UrgencyLevel.MEDIUM: 2,
    UrgencyLevel.NORMAL: 3,
}


@router.get(
    "/",
    response_model=ApplicationListResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.BORROWER,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def list_applications(
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    sort_by: Literal["urgency", "updated_at", "loan_amount"] | None = None,
    filter_stage: ApplicationStage | None = None,
    filter_stalled: bool = Query(default=False),
) -> ApplicationListResponse:
    """List applications visible to the current user's role and data scope."""
    applications, total = await app_service.list_applications(
        session,
        user,
        offset=offset,
        limit=limit,
        filter_stage=filter_stage,
        filter_stalled=filter_stalled,
        sort_by=sort_by if sort_by != "urgency" else None,
    )

    items = [_build_app_response(app) for app in applications]

    # Enrich with urgency for LO/admin roles
    if user.role in _URGENCY_ROLES and applications:
        urgency_map = await compute_urgency(session, list(applications))
        for item in items:
            item.urgency = urgency_map.get(item.id)

        # Post-query sort by urgency level
        if sort_by == "urgency":
            items.sort(
                key=lambda x: _URGENCY_ORDER.get(
                    x.urgency.level if x.urgency else UrgencyLevel.NORMAL,
                    3,
                )
            )

    return ApplicationListResponse(
        data=items,
        pagination=Pagination(
            total=total,
            offset=offset,
            limit=limit,
            has_more=(offset + limit < total),
        ),
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.BORROWER,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def get_application(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Get a single application. Returns 404 for out-of-scope resources."""
    app = await app_service.get_application(session, user, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return _build_app_response(app)


@router.get(
    "/{application_id}/status",
    response_model=ApplicationStatusResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.BORROWER,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def get_status(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApplicationStatusResponse:
    """Get aggregated status summary for an application."""
    result = await get_application_status(session, user, application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return result


@router.get(
    "/{application_id}/rate-lock",
    response_model=RateLockResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.BORROWER,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def get_rate_lock(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> RateLockResponse:
    """Get rate lock status for an application."""
    result = await get_rate_lock_status(session, user, application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return RateLockResponse(**result)


@router.get(
    "/{application_id}/conditions",
    response_model=ConditionListResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.BORROWER,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
            )
        )
    ],
)
async def list_conditions(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    open_only: bool = Query(default=False),
) -> ConditionListResponse:
    """List conditions for an application."""
    result = await get_conditions(session, user, application_id, open_only=open_only)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    return ConditionListResponse(
        data=result,
        pagination=Pagination(
            total=len(result),
            offset=0,
            limit=len(result),
            has_more=False,
        ),
    )


@router.post(
    "/{application_id}/conditions/{condition_id}/respond",
    response_model=ConditionResponse,
    dependencies=[Depends(require_roles(UserRole.BORROWER, UserRole.ADMIN))],
)
async def respond_condition(
    application_id: int,
    condition_id: int,
    body: ConditionRespondRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
):
    """Record a borrower's text response to a condition."""
    result = await respond_to_condition(
        session,
        user,
        application_id,
        condition_id,
        body.response_text,
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application or condition not found",
        )
    return ConditionResponse(data=ConditionItem(**result))


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
) -> ApplicationResponse:
    """Create a new application. Borrowers and admins only."""
    app = await app_service.create_application(
        session,
        user,
        loan_type=body.loan_type,
        property_address=body.property_address,
        loan_amount=body.loan_amount,
        property_value=body.property_value,
    )
    return _build_app_response(app)


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
            )
        )
    ],
)
async def update_application(
    application_id: int,
    body: ApplicationUpdate,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Update an application. LOs, underwriters, and admins only."""
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No fields to update",
        )

    # Stage transitions go through the state machine
    new_stage = updates.pop("stage", None)
    app = None

    if new_stage is not None:
        app = await app_service.transition_stage(
            session,
            user,
            application_id,
            new_stage,
        )
        if app is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

    if updates:
        app = await app_service.update_application(
            session,
            user,
            application_id,
            **updates,
        )
        if app is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found",
            )

    return _build_app_response(app)


@router.post(
    "/{application_id}/borrowers",
    response_model=ApplicationResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[
        Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))
    ],
)
async def add_borrower(
    application_id: int,
    body: AddBorrowerRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Add a borrower to an application (co-borrower management)."""
    app = await app_service.get_application(session, user, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Verify borrower exists
    borrower_result = await session.execute(select(Borrower).where(Borrower.id == body.borrower_id))
    if borrower_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not found",
        )

    # Check for duplicate junction row
    dup_result = await session.execute(
        select(ApplicationBorrower).where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.borrower_id == body.borrower_id,
        )
    )
    if dup_result.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Borrower already linked to this application",
        )

    junction = ApplicationBorrower(
        application_id=application_id,
        borrower_id=body.borrower_id,
        is_primary=body.is_primary,
    )
    session.add(junction)
    await session.commit()

    refreshed = await app_service.get_application(session, user, application_id)
    return _build_app_response(refreshed)


@router.delete(
    "/{application_id}/borrowers/{borrower_id}",
    response_model=ApplicationResponse,
    dependencies=[
        Depends(require_roles(UserRole.LOAN_OFFICER, UserRole.UNDERWRITER, UserRole.ADMIN))
    ],
)
async def remove_borrower(
    application_id: int,
    borrower_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> ApplicationResponse:
    """Remove a borrower from an application."""
    app = await app_service.get_application(session, user, application_id)
    if app is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )

    # Find the junction row
    junction_result = await session.execute(
        select(ApplicationBorrower).where(
            ApplicationBorrower.application_id == application_id,
            ApplicationBorrower.borrower_id == borrower_id,
        )
    )
    junction = junction_result.scalar_one_or_none()
    if junction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Borrower not linked to this application",
        )

    # Count remaining borrowers (must keep at least one)
    from sqlalchemy import func

    count_result = await session.execute(
        select(func.count()).where(ApplicationBorrower.application_id == application_id)
    )
    if count_result.scalar() <= 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the last borrower from an application",
        )

    # Cannot remove primary without reassigning first
    if junction.is_primary:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot remove the primary borrower. Reassign primary first.",
        )

    await session.delete(junction)
    await session.commit()

    refreshed = await app_service.get_application(session, user, application_id)
    return _build_app_response(refreshed)
