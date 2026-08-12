from datetime import datetime
from typing import Any
from uuid import UUID

from app.core.constants import InvestigationStatus
from app.schemas.common import ORMModel


class StepExecutionRead(ORMModel):
    id: UUID
    investigation_id: UUID
    step_name: str
    step_order: int
    status: InvestigationStatus
    started_at: datetime
    completed_at: datetime | None = None
    output: dict[str, Any]
    error: str | None = None
