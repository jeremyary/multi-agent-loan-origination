# This project was developed with assistance from AI tools.
"""Document completeness request/response schemas."""

from db.enums import DocumentStatus, DocumentType
from pydantic import BaseModel


class DocumentRequirement(BaseModel):
    """A single required document with its fulfillment status."""

    doc_type: DocumentType
    label: str
    is_provided: bool = False
    document_id: int | None = None
    status: DocumentStatus | None = None
    quality_flags: list[str] = []


class CompletenessResponse(BaseModel):
    """Document completeness summary for an application."""

    application_id: int
    is_complete: bool
    requirements: list[DocumentRequirement]
    provided_count: int
    required_count: int
