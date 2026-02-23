"""
Health check schemas
"""


from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Health check response schema"""
    
    name: str
    status: str
    message: str
    version: str
    start_time: str | None = None
