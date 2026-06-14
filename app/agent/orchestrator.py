from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Sequence, TypeVar
from uuid import UUID

from app.agent.state import AgentState
from app.agent.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)
from app.agent.steps.base import AgentStep
from app.core.constants import IncidentStatus
from app.core.constants import IncidentSeverity
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)
StepT = TypeVar("StepT", bound=AgentStep)


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
        log_step = self._require_step(LogAnalysisStep)
        knowledge_step = self._require_step(KnowledgeRetrievalStep)
        root_cause_step = self._require_step(RootCauseAnalysisStep)
        remediation_step = self._require_step(RemediationPlanningStep)
        report_step = self._require_step(ReportGenerationStep)

        await self.investigation_service.mark_running(investigation_id)

        try:
            state = await self._run_step(investigation_id=investigation_id, step=log_step, state=state)

            severity = state.log_signals.severity_assessment if state.log_signals is not None else IncidentSeverity.MEDIUM
            retrieval_top_k = 8 if severity in {IncidentSeverity.CRITICAL, IncidentSeverity.HIGH} else 3
            if retrieval_top_k == 8:
                logger.info(
                    "Agent decision: %s severity, running full knowledge retrieval (top_k=8)",
                    severity.value,
                )
            else:
                logger.info(
                    "Agent decision: %s severity, running lighter knowledge retrieval (top_k=3)",
                    severity.value,
                )

            state = await self._run_knowledge_step(
                investigation_id=investigation_id,
                step=knowledge_step,
                state=state,
                top_k=retrieval_top_k,
            )
            state = await self._run_step(
                investigation_id=investigation_id,
                step=root_cause_step,
                state=state,
            )

            confidence_score = state.root_cause.confidence_score if state.root_cause is not None else None
            if confidence_score is not None and confidence_score < 0.75 and not state.root_cause_retried:
                state.root_cause_retried = True
                logger.info(
                    "Agent decision: low confidence (%.2f), retrying root cause with expanded context",
                    confidence_score,
                )
                state = await self._run_knowledge_step(
                    investigation_id=investigation_id,
                    step=knowledge_step,
                    state=state,
                    top_k=max(retrieval_top_k, 8),
                    query_suffix=state.root_cause.primary_cause,
                )
                state = await self._run_step(
                    investigation_id=investigation_id,
                    step=root_cause_step,
                    state=state,
                )

            state = await self._run_step(
                investigation_id=investigation_id,
                step=remediation_step,
                state=state,
            )

            remediation_count = len(state.remediation.steps) if state.remediation is not None else 0
            if remediation_count < 2 and not state.remediation_retried:
                state.remediation_retried = True
                logger.info(
                    "Agent decision: only %s remediation steps generated, retrying",
                    remediation_count,
                )
                state = await self._run_step(
                    investigation_id=investigation_id,
                    step=remediation_step,
                    state=state,
                )

            state = await self._run_step(
                investigation_id=investigation_id,
                step=report_step,
                state=state,
            )
            self._annotate_report_retries(state)

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

    async def _run_step(
        self,
        *,
        investigation_id: UUID,
        step: AgentStep,
        state: AgentState,
    ) -> AgentState:
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
        return state

    async def _run_knowledge_step(
        self,
        *,
        investigation_id: UUID,
        step: KnowledgeRetrievalStep,
        state: AgentState,
        top_k: int,
        query_suffix: str | None = None,
    ) -> AgentState:
        await self.investigation_service.mark_step_started(
            investigation_id=investigation_id,
            step_name=step.name,
        )
        state = await step.execute(state, top_k=top_k, query_suffix=query_suffix)
        await self.investigation_service.record_step_completion(
            investigation_id=investigation_id,
            step_name=step.name,
            step_order=step.order,
            output=step.build_output(state),
        )
        return state

    def _require_step(self, step_type: type[StepT]) -> StepT:
        for step in self.steps:
            if isinstance(step, step_type):
                return step
        raise LookupError(f"Required step {step_type.__name__} was not configured.")

    @staticmethod
    def _annotate_report_retries(state: AgentState) -> None:
        if state.report is None:
            return
        if state.root_cause_retried and "retry" not in state.report.root_cause_section.lower():
            state.report.root_cause_section = (
                f"{state.report.root_cause_section} "
                "This finding was refined after a retry with expanded knowledge context."
            ).strip()
