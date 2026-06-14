from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence
from uuid import UUID

from app.agent.state import AgentState
from app.agent.steps.base import AgentStep
from app.core.constants import IncidentStatus
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService


@dataclass(slots=True)
class AgentOrchestrator:
    steps: Sequence[AgentStep]
    incident_service: IncidentService
    investigation_service: InvestigationService
    report_service: ReportService

    async def run(self, investigation_id: UUID) -> AgentState:
        investigation = await self._require_investigation(investigation_id)
        incident = await self._require_incident(investigation.incident_id)
        state = self._build_initial_state(incident=incident, investigation=investigation)

        await self.investigation_service.mark_running(investigation_id)

        try:
            for step in self.steps:
                await self.investigation_service.mark_step_started(
                    investigation_id=investigation_id,
                    step_name=step.name,
                )
                state = await step.execute(state)
                await self.investigation_service.record_step_completion(
                    investigation_id=investigation_id,
                    step_name=step.name,
                    step_order=step.order,
                    output=step.build_output(state),
                )

            await self.report_service.create(
                investigation_id=state.investigation_id,
                report_data=state.to_report_payload(),
            )
            await self.investigation_service.mark_completed(investigation_id)
            await self.incident_service.update_status(
                incident_id=state.incident_id,
                status=IncidentStatus.RESOLVED,
            )
            return state
        except Exception as exc:
            await self.investigation_service.mark_failed(
                investigation_id=investigation_id,
                error=str(exc),
            )
            raise

    def _build_initial_state(
        self,
        *,
        incident: Incident,
        investigation: Investigation,
    ) -> AgentState:
        environment = incident.environment.value if incident.environment is not None else None

        return AgentState(
            investigation_id=investigation.id,
            incident_id=incident.id,
            incident_title=incident.title,
            incident_description=incident.description,
            raw_log=incident.raw_log,
            incident_metadata=dict(incident.metadata_),
            service_name=incident.service_name,
            source=incident.source,
            environment=environment,
        )

    async def _require_investigation(self, investigation_id: UUID) -> Investigation:
        investigation = await self.investigation_service.get_by_id(investigation_id)
        if investigation is None:
            raise LookupError(f"Investigation {investigation_id} was not found.")
        return investigation

    async def _require_incident(self, incident_id: UUID) -> Incident:
        incident = await self.incident_service.get_by_id(incident_id)
        if incident is None:
            raise LookupError(f"Incident {incident_id} was not found.")
        return incident

    @staticmethod
    def utcnow() -> datetime:
        return datetime.now(timezone.utc)
