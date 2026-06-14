from datetime import datetime
from uuid import UUID

from app.core.constants import InvestigationStatus
from app.schemas.common import AuditRead, ORMModel


class InvestigationBase(ORMModel):
    incident_id: UUID
    status: InvestigationStatus = InvestigationStatus.QUEUED
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class InvestigationCreate(InvestigationBase):
    pass


class InvestigationUpdate(ORMModel):
    status: InvestigationStatus | None = None
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


class InvestigationRead(InvestigationBase, AuditRead):
    pass


class InvestigationRunRequest(ORMModel):
    incident_id: UUID


class InvestigationRunResponse(ORMModel):
    investigation: InvestigationRead
    report_id: UUID | None = None
