# This project was developed with assistance from AI tools.
"""Product information schemas."""

from pydantic import BaseModel


class ProductInfo(BaseModel):
    """Mortgage product information for public display."""

    id: str
    name: str
    description: str
    min_down_payment_pct: float
    typical_rate: float
