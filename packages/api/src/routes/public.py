# This project was developed with assistance from AI tools.
"""Public API routes -- no authentication required."""

from fastapi import APIRouter

from ..schemas.calculator import AffordabilityRequest, AffordabilityResponse
from ..schemas.products import ProductInfo
from ..services.calculator import calculate_affordability as _calculate

router = APIRouter()

PRODUCTS: list[ProductInfo] = [
    ProductInfo(
        id="conventional_30",
        name="30-Year Fixed Conventional",
        description="Standard fixed-rate mortgage with predictable monthly payments over 30 years. "
        "Ideal for buyers planning to stay long-term.",
        min_down_payment_pct=3.0,
        typical_rate=6.5,
    ),
    ProductInfo(
        id="conventional_15",
        name="15-Year Fixed Conventional",
        description="Fixed-rate mortgage with a shorter term. Higher monthly payments but "
        "significantly less total interest paid.",
        min_down_payment_pct=3.0,
        typical_rate=5.75,
    ),
    ProductInfo(
        id="fha",
        name="FHA Loan",
        description="Government-backed loan with lower credit score and down payment requirements. "
        "Requires mortgage insurance premium (MIP).",
        min_down_payment_pct=3.5,
        typical_rate=6.25,
    ),
    ProductInfo(
        id="va",
        name="VA Loan",
        description="Available to eligible veterans and service members. No down payment required "
        "and no private mortgage insurance.",
        min_down_payment_pct=0.0,
        typical_rate=6.0,
    ),
    ProductInfo(
        id="jumbo",
        name="Jumbo Loan",
        description="For loan amounts exceeding conforming limits. Typically requires higher credit "
        "scores and larger down payments.",
        min_down_payment_pct=10.0,
        typical_rate=6.75,
    ),
    ProductInfo(
        id="usda",
        name="USDA Loan",
        description="Zero down payment loan for eligible rural and suburban properties. "
        "Income limits apply.",
        min_down_payment_pct=0.0,
        typical_rate=6.25,
    ),
]


@router.get("/products", response_model=list[ProductInfo])
async def list_products() -> list[ProductInfo]:
    """Return available mortgage products. No authentication required."""
    return PRODUCTS


@router.post("/calculate-affordability", response_model=AffordabilityResponse)
async def calculate_affordability(req: AffordabilityRequest) -> AffordabilityResponse:
    """Estimate maximum loan amount and monthly payment."""
    return _calculate(req)
