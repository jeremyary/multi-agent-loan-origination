# This project was developed with assistance from AI tools.
"""Public API routes -- no authentication required."""

from fastapi import APIRouter

from ..schemas.calculator import AffordabilityRequest, AffordabilityResponse
from ..schemas.products import ProductInfo
from ..services.calculator import calculate_affordability as _calculate
from ..services.products import PRODUCTS

router = APIRouter()


@router.get("/products", response_model=list[ProductInfo])
async def list_products() -> list[ProductInfo]:
    """Return available mortgage products. No authentication required."""
    return PRODUCTS


@router.post("/calculate-affordability", response_model=AffordabilityResponse)
async def calculate_affordability(req: AffordabilityRequest) -> AffordabilityResponse:
    """Estimate maximum loan amount and monthly payment."""
    return _calculate(req)
