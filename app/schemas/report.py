from datetime import datetime
from uuid import UUID

from pydantic import Field

from app.schemas.common import ORMModel, TimelineEntry


class ReportBase(ORMModel):
    investigation_id: UUID
    incident_id: UUID
    title: str = Field(min_length=1, max_length=500)
    executive_summary: str = Field(min_length=1, max_length=20000)
    incident_summary: str = Field(min_length=1, max_length=20000)
    root_cause_section: str = Field(min_length=1, max_length=20000)
    evidence_section: str = Field(min_length=1, max_length=20000)
    remediation_section: str = Field(min_length=1, max_length=20000)
    timeline: list[TimelineEntry] = Field(default_factory=list)
    format_version: str = "1.0"


class ReportCreate(ReportBase):
    generated_at: datetime


class ReportRead(ReportBase):
    id: UUID
    generated_at: datetime
