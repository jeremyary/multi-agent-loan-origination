# This project was developed with assistance from AI tools.
"""Application status response schemas."""

from pydantic import BaseModel

from .urgency import UrgencyIndicator


class PendingAction(BaseModel):
    """A single action the borrower or LO needs to take."""

    action_type: str
    description: str


class StageInfo(BaseModel):
    """Human-readable info about the current application stage."""

    label: str
    description: str
    next_step: str
    typical_timeline: str


class ApplicationStatusResponse(BaseModel):
    """Aggregated status summary for an application."""

    application_id: int
    stage: str
    stage_info: StageInfo
    is_document_complete: bool
    provided_doc_count: int
    required_doc_count: int
    open_condition_count: int
    pending_actions: list[PendingAction]
    urgency: UrgencyIndicator | None = None
