from datetime import datetime
from uuid import UUID

from pydantic import Field
from typing import Any

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
    evidence_refs: list[dict[str, Any]] = Field(default_factory=list)
    remediation_steps: list[dict[str, Any]] = Field(default_factory=list)
    root_cause_retried: bool = False
    remediation_retried: bool = False
    confidence_score: float | None = Field(default=None, ge=0, le=1)
    format_version: str = "1.0"


class ReportCreate(ReportBase):
    generated_at: datetime


class ReportRead(ReportBase):
    id: UUID
    generated_at: datetime
