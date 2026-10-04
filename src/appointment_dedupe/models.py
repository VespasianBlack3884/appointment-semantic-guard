from typing import Literal

from pydantic import BaseModel, Field


class AppointmentRecord(BaseModel):
    appointment_id: str = Field(min_length=1)
    patient_id: str = Field(min_length=1)
    clinic: str = Field(min_length=1)
    starts_at: str = Field(min_length=1)
    reason: str = Field(min_length=1)


class DuplicateCandidate(BaseModel):
    appointment_id: str
    score: float


class AppointmentDecision(BaseModel):
    appointment_id: str
    status: Literal["accepted", "review_required"]
    duplicate_of: str | None
    semantic_score: float | None
    notification: str

