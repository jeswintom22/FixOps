from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Any

from app.agent.state import AgentState, LogSignals
from app.agent.steps.base import AgentStep
from app.core.constants import IncidentSeverity
from app.services.azure_ai_service import AzureAIService


@dataclass(slots=True)
class LogAnalysisStep(AgentStep):
    azure_ai_service: AzureAIService
    name: str = "LOG_ANALYSIS"
    order: int = 1

    async def execute(self, state: AgentState) -> AgentState:
        response = await self.azure_ai_service.structured_complete(
            prompt=self._build_prompt(state),
            schema=LogSignalsResponse,
        )
        state.log_signals = response.to_domain()
        return state

    def build_output(self, state: AgentState) -> dict[str, Any]:
        if state.log_signals is None:
            return {}
        payload = asdict(state.log_signals)
        start, end = state.log_signals.timestamp_range
        payload["timestamp_range"] = {
            "start": start.isoformat() if start is not None else None,
            "end": end.isoformat() if end is not None else None,
        }
        payload["severity_assessment"] = state.log_signals.severity_assessment.value
        return payload

    def _build_prompt(self, state: AgentState) -> str:
        return "\n".join(
            [
                "Analyze the incident log and extract structured operational signals.",
                f"Incident title: {state.incident_title}",
                f"Service name: {state.service_name or 'unknown'}",
                f"Source: {state.source or 'unknown'}",
                f"Environment: {state.environment or 'unknown'}",
                "Raw log:",
                state.raw_log,
            ]
        )


@dataclass(slots=True)
class LogSignalsResponse:
    error_type: str
    affected_service: str | None = None
    key_terms: list[str] | None = None
    anomaly_signals: list[str] | None = None
    timestamp_start: datetime | None = None
    timestamp_end: datetime | None = None
    severity_assessment: IncidentSeverity = IncidentSeverity.MEDIUM

    def to_domain(self) -> LogSignals:
        return LogSignals(
            error_type=self.error_type,
            affected_service=self.affected_service,
            key_terms=list(self.key_terms or []),
            anomaly_signals=list(self.anomaly_signals or []),
            timestamp_range=(self.timestamp_start, self.timestamp_end),
            severity_assessment=self.severity_assessment,
        )
