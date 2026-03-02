# This project was developed with assistance from AI tools.
"""HMDA demographic data collection schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class HmdaCollectionRequest(BaseModel):
    """Request body for HMDA demographic data collection."""

    application_id: int
    borrower_id: int | None = None
    race: str | None = None
    ethnicity: str | None = None
    sex: str | None = None
    age: str | None = None
    race_collected_method: str = Field(default="self_reported")
    ethnicity_collected_method: str = Field(default="self_reported")
    sex_collected_method: str = Field(default="self_reported")
    age_collected_method: str = Field(default="self_reported")


class HmdaDemographicConflict(BaseModel):
    """A single conflict detected during HMDA demographic collection."""

    field: str
    existing_value: str | None = None
    new_value: str | None = None
    resolution: str | None = None


class HmdaCollectionResponse(BaseModel):
    """Response after collecting HMDA demographic data."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    application_id: int
    borrower_id: int | None = None
    collected_at: datetime
    conflicts: list[HmdaDemographicConflict] | None = None
    status: str = "collected"
