# This project was developed with assistance from AI tools.
"""Shared schema components."""

from pydantic import BaseModel


class Pagination(BaseModel):
    """Offset-based pagination metadata for list responses."""

    total: int
    offset: int
    limit: int
    has_more: bool
