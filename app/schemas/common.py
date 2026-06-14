from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True, extra="forbid")


class TimestampedRead(ORMModel):
    id: UUID
    created_at: datetime


class AuditRead(TimestampedRead):
    updated_at: datetime


class TimelineEntry(ORMModel):
    timestamp: datetime
    event: str


class MetadataEnvelope(ORMModel):
    metadata: dict[str, Any] = Field(default_factory=dict)
