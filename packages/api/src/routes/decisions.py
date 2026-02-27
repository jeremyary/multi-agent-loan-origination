# This project was developed with assistance from AI tools.
"""Decision REST endpoints (read-only)."""

from db import get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import CurrentUser, require_roles
from ..schemas import Pagination
from ..schemas.decision import DecisionItem, DecisionListResponse, DecisionResponse
from ..services.decision import get_decisions

router = APIRouter()


@router.get(
    "/{application_id}/decisions",
    response_model=DecisionListResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def list_decisions(
    application_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> DecisionListResponse:
    """List all decisions for an application."""
    result = await get_decisions(session, user, application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    items = [DecisionItem(**d) for d in result]
    return DecisionListResponse(
        data=items,
        pagination=Pagination(
            total=len(items),
            offset=0,
            limit=len(items),
            has_more=False,
        ),
    )


@router.get(
    "/{application_id}/decisions/{decision_id}",
    response_model=DecisionResponse,
    dependencies=[
        Depends(
            require_roles(
                UserRole.ADMIN,
                UserRole.LOAN_OFFICER,
                UserRole.UNDERWRITER,
                UserRole.CEO,
            )
        )
    ],
)
async def get_decision(
    application_id: int,
    decision_id: int,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
) -> DecisionResponse:
    """Get a single decision by ID."""
    result = await get_decisions(session, user, application_id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found",
        )
    for d in result:
        if d["id"] == decision_id:
            return DecisionResponse(data=DecisionItem(**d))
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail="Decision not found",
    )
