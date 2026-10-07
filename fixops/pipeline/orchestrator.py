from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TypeVar

from fixops.db import IncidentSeverity, InvestigationStatus
from fixops.pipeline.state import AgentState, StepExecution
from fixops.pipeline.steps.base import AgentStep
from fixops.pipeline.steps.knowledge_retriever import KnowledgeRetrievalStep, select_top_k
from fixops.pipeline.steps.log_analyzer import LogAnalysisStep
from fixops.pipeline.steps.remediation_planner import RemediationPlanningStep
from fixops.pipeline.steps.report_generator import ReportGenerationStep
from fixops.pipeline.steps.root_cause_analyzer import RootCauseAnalysisStep

logger = logging.getLogger(__name__)
StepT = TypeVar("StepT", bound=AgentStep)


@dataclass
class AgentOrchestrator:
    steps: Sequence[AgentStep]
    confidence_threshold: float = 0.75
    min_remediation_steps: int = 2

    async def run(self, initial_state: AgentState) -> AgentState:
        state = initial_state
        log_step = self._require_step(LogAnalysisStep)
        knowledge_step = self._require_step(KnowledgeRetrievalStep)
        root_cause_step = self._require_step(RootCauseAnalysisStep)
        remediation_step = self._require_step(RemediationPlanningStep)
        report_step = self._require_step(ReportGenerationStep)

        try:
            state = await self._run_step(step=log_step, state=state)

            severity = (
                state.log_signals.severity_assessment
                if state.log_signals
                else IncidentSeverity.MEDIUM
            )
            top_k = select_top_k(severity)
            logger.info("Knowledge retrieval: severity=%s top_k=%d", severity.value, top_k)
            state = await self._run_knowledge_step(
                step=knowledge_step,
                state=state,
                top_k=top_k,
            )
            state = await self._run_step(step=root_cause_step, state=state)

            confidence = state.root_cause.confidence_score if state.root_cause else None
            if (
                confidence is not None
                and confidence < self.confidence_threshold
                and not state.root_cause_retried
            ):
                assert state.root_cause is not None
                state.root_cause_retried = True
                logger.info(
                    "Low confidence (%.2f); retrying root cause with expanded context", confidence
                )
                state = await self._run_knowledge_step(
                    step=knowledge_step,
                    state=state,
                    top_k=max(top_k, 8),
                    query_suffix=state.root_cause.primary_cause,
                )
                state = await self._run_step(step=root_cause_step, state=state)

            state = await self._run_step(step=remediation_step, state=state)

            remediation_count = len(state.remediation.steps) if state.remediation else 0
            if remediation_count < self.min_remediation_steps and not state.remediation_retried:
                state.remediation_retried = True
                logger.info("Only %s remediation steps; retrying planning", remediation_count)
                state = await self._run_step(step=remediation_step, state=state)

            state = await self._run_step(step=report_step, state=state)
            self._annotate_report_retries(state)
            return state
        except Exception:
            logger.exception("Pipeline failed for investigation %s", state.investigation_id)
            raise

    async def _run_step(self, *, step: AgentStep, state: AgentState) -> AgentState:
        started_at = datetime.now(timezone.utc)
        execution = StepExecution(
            step_name=step.name,
            step_order=step.order,
            status=InvestigationStatus.RUNNING,
            started_at=started_at,
        )
        state.step_history.append(execution)
        try:
            state = await step.execute(state)
            execution.status = InvestigationStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            execution.output = dict(step.build_output(state))
        except Exception as exc:
            execution.status = InvestigationStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = str(exc)
            raise
        return state

    async def _run_knowledge_step(
        self,
        *,
        step: KnowledgeRetrievalStep,
        state: AgentState,
        top_k: int,
        query_suffix: str | None = None,
    ) -> AgentState:
        started_at = datetime.now(timezone.utc)
        execution = StepExecution(
            step_name=step.name,
            step_order=step.order,
            status=InvestigationStatus.RUNNING,
            started_at=started_at,
        )
        state.step_history.append(execution)
        try:
            state = await step.execute(state, top_k=top_k, query_suffix=query_suffix)
            execution.status = InvestigationStatus.COMPLETED
            execution.completed_at = datetime.now(timezone.utc)
            execution.output = dict(step.build_output(state))
        except Exception as exc:
            execution.status = InvestigationStatus.FAILED
            execution.completed_at = datetime.now(timezone.utc)
            execution.error = str(exc)
            raise
        return state

    def _require_step(self, step_type: type[StepT]) -> StepT:
        for step in self.steps:
            if isinstance(step, step_type):
                return step
        raise LookupError(f"Required step {step_type.__name__} was not configured")

    @staticmethod
    def _annotate_report_retries(state: AgentState) -> None:
        if state.report is None:
            return
        if state.root_cause_retried and "retry" not in state.report.root_cause_section.lower():
            state.report.root_cause_section = (
                f"{state.report.root_cause_section} "
                "This finding was refined after a retry with expanded knowledge context."
            ).strip()
