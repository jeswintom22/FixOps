from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, field
from datetime import datetime, timezone
from typing import Any

from pydantic.dataclasses import dataclass

from fixops.llm.base import LLMService, Message
from fixops.pipeline.state import AgentState, ReportResult, TimelineEvent
from fixops.pipeline.steps.base import AgentStep


@dataclass
class TimelineEventSchema:
    timestamp: datetime
    event: str


@dataclass
class ReportResponse:
    title: str
    executive_summary: str
    incident_summary: str
    root_cause_section: str
    evidence_section: str
    remediation_section: str
    timeline: list[TimelineEventSchema] | None = None
    format_version: str = "1.0"
    generated_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )

    def to_domain(self) -> ReportResult:
        return ReportResult(
            title=self.title,
            executive_summary=self.executive_summary,
            incident_summary=self.incident_summary,
            root_cause_section=self.root_cause_section,
            evidence_section=self.evidence_section,
            remediation_section=self.remediation_section,
            timeline=[
                TimelineEvent(timestamp=item.timestamp, event=item.event)
                for item in self.timeline or []
            ],
            format_version=self.format_version,
            generated_at=self.generated_at,
        )


class ReportGenerationStep(AgentStep):
    name = "REPORT_GENERATION"
    order = 5

    def __init__(self, llm_service: LLMService) -> None:
        self.llm_service = llm_service

    async def execute(self, state: AgentState) -> AgentState:
        if state.root_cause is None or state.remediation is None:
            raise ValueError("Root cause analysis and remediation planning must complete first")

        response = await self.llm_service.structured_complete(
            messages=[Message(role="user", content=self._build_prompt(state))],
            schema=ReportResponse,
        )
        state.report = response.to_domain()
        if state.report.generated_at is None:
            state.report.generated_at = datetime.now(timezone.utc)
        return state

    def build_output(self, state: AgentState) -> Mapping[str, Any]:
        if state.report is None:
            return {}
        payload = asdict(state.report)
        payload["timeline"] = [
            {"timestamp": event.timestamp.isoformat(), "event": event.event}
            for event in state.report.timeline
        ]
        payload["generated_at"] = state.report.generated_at.isoformat()
        return payload

    def _build_prompt(self, state: AgentState) -> str:
        from fixops.config import get_settings
        from fixops.pipeline.steps.log_analyzer import _trim_log_tail

        budget = get_settings().raw_log_prompt_budget
        raw_log_excerpt = _trim_log_tail(state.raw_log, budget)
        return "\n".join(
            [
                "Assemble the final investigation report. Derive the timeline from the "
                "log timestamps and the analysis steps.",
                f"Incident title: {state.incident_title}",
                f"Incident description: {state.incident_description or 'n/a'}",
                "Raw log:",
                raw_log_excerpt,
                f"Log signals: {state.log_signals}",
                f"Root cause: {state.root_cause}",
                f"Remediation plan: {state.remediation}",
                f"Knowledge chunks used: {state.knowledge_chunks}",
            ]
        )
