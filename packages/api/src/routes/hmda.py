# This project was developed with assistance from AI tools.
"""HMDA demographic data collection endpoint."""

from db import get_compliance_db, get_db
from db.enums import UserRole
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from ..middleware.auth import CurrentUser, require_roles
from ..schemas.hmda import HmdaCollectionRequest, HmdaCollectionResponse
from ..services.compliance.hmda import collect_demographics

router = APIRouter()


@router.post(
    "/collect",
    response_model=HmdaCollectionResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.BORROWER, UserRole.ADMIN))],
)
async def collect_hmda(
    body: HmdaCollectionRequest,
    user: CurrentUser,
    session: AsyncSession = Depends(get_db),
    compliance_session: AsyncSession = Depends(get_compliance_db),
):
    """Collect HMDA demographic data for an application.

    Simulated for demonstration purposes -- not legally compliant HMDA collection.
    """
    try:
        demographic = await collect_demographics(
            lending_session=session,
            compliance_session=compliance_session,
            user=user,
            request=body,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    return HmdaCollectionResponse.model_validate(demographic)
