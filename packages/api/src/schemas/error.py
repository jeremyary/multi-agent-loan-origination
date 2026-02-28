# This project was developed with assistance from AI tools.
"""RFC 7807 Problem Details error response schema."""

from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """RFC 7807 Problem Details for HTTP APIs.

    See https://datatracker.ietf.org/doc/html/rfc7807
    """

    type: str = Field(
        default="about:blank",
        description="URI reference identifying the problem type.",
    )
    title: str = Field(description="Short human-readable summary of the problem.")
    status: int = Field(description="HTTP status code.")
    detail: str = Field(
        default="",
        description="Human-readable explanation specific to this occurrence.",
    )
    request_id: str = Field(
        default="",
        description="Correlation ID for tracing this request in logs.",
    )
    instance: str = Field(
        default="",
        description="URI reference identifying the specific occurrence of the problem.",
    )
