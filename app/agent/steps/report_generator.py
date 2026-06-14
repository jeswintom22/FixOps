from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from typing import Any

from app.agent.state import AgentState, ReportResult, TimelineEvent
from app.agent.steps.base import AgentStep
from app.services.azure_ai_service import AzureAIService


@dataclass(slots=True)
class ReportGenerationStep(AgentStep):
    azure_ai_service: AzureAIService
    name: str = "REPORT_GENERATION"
    order: int = 5

    async def execute(self, state: AgentState) -> AgentState:
        if state.root_cause is None or state.remediation is None:
            raise ValueError("Root cause analysis and remediation planning must complete first.")

        response = await self.azure_ai_service.structured_complete(
            prompt=self._build_prompt(state),
            schema=ReportResponse,
        )
        state.report = response.to_domain()
        return state

    def build_output(self, state: AgentState) -> dict[str, Any]:
        if state.report is None:
            return {}
        payload = asdict(state.report)
        payload["timeline"] = [
            {
                "timestamp": event.timestamp.isoformat(),
                "event": event.event,
            }
            for event in state.report.timeline
        ]
        payload["generated_at"] = state.report.generated_at.isoformat()
        return payload

    def _build_prompt(self, state: AgentState) -> str:
        return "\n".join(
            [
                "Assemble the final investigation report.",
                f"Incident title: {state.incident_title}",
                f"Incident description: {state.incident_description or 'n/a'}",
                f"Raw log: {state.raw_log}",
                f"Log signals: {state.log_signals}",
                f"Root cause: {state.root_cause}",
                f"Remediation plan: {state.remediation}",
                f"Knowledge chunks used: {state.knowledge_chunks}",
            ]
        )


@dataclass(slots=True)
class ReportResponse:
    title: str
    executive_summary: str
    incident_summary: str
    root_cause_section: str
    evidence_section: str
    remediation_section: str
    timeline: list[dict[str, Any]] | None = None
    format_version: str = "1.0"
    generated_at: datetime | None = None

    def to_domain(self) -> ReportResult:
        return ReportResult(
            title=self.title,
            executive_summary=self.executive_summary,
            incident_summary=self.incident_summary,
            root_cause_section=self.root_cause_section,
            evidence_section=self.evidence_section,
            remediation_section=self.remediation_section,
            timeline=[
                TimelineEvent(
                    timestamp=_coerce_datetime(item.get("timestamp")),
                    event=str(item.get("event", "")),
                )
                for item in self.timeline or []
            ],
            format_version=self.format_version,
            generated_at=self.generated_at or datetime.now(UTC),
        )


def _coerce_datetime(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    raise TypeError("Timeline timestamps must be datetime or ISO 8601 strings.")
