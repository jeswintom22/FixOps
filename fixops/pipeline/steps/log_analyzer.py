from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from datetime import datetime
from typing import Any

from pydantic.dataclasses import dataclass

from fixops.config import get_settings
from fixops.db import IncidentSeverity
from fixops.llm.base import LLMService, Message
from fixops.pipeline.state import AgentState, LogSignals
from fixops.pipeline.steps.base import AgentStep


@dataclass
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


class LogAnalysisStep(AgentStep):
    name = "LOG_ANALYSIS"
    order = 1

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def execute(self, state: AgentState) -> AgentState:
        response = await self.llm_service.structured_complete(
            messages=[Message(role="user", content=self._build_prompt(state))],
            schema=LogSignalsResponse,
        )
        state.log_signals = response.to_domain()
        return state

    def build_output(self, state: AgentState) -> Mapping[str, Any]:
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
        budget = get_settings().raw_log_prompt_budget
        trimmed = _trim_log_tail(state.raw_log, budget)
        return "\n".join(
            [
                "Analyze the incident log and extract structured operational signals.",
                f"Incident title: {state.incident_title}",
                f"Service name: {state.service_name or 'unknown'}",
                f"Source: {state.source or 'unknown'}",
                f"Environment: {state.environment or 'unknown'}",
                "Raw log:",
                trimmed,
            ]
        )


def _trim_log_tail(raw_log: str, budget: int) -> str:
    """Preserve the tail of the log because errors are usually at the end."""
    if len(raw_log) <= budget:
        return raw_log
    tail = raw_log[-budget:]
    # Avoid starting mid-line if possible.
    if "\n" in tail and not tail.startswith("\n"):
        return tail[tail.index("\n") + 1 :]
    return tail
