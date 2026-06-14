from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from app.core.constants import IncidentSeverity, InvestigationStatus, KnowledgeCategory


@dataclass(slots=True)
class LogSignals:
    error_type: str
    affected_service: str | None
    key_terms: list[str] = field(default_factory=list)
    anomaly_signals: list[str] = field(default_factory=list)
    timestamp_range: tuple[datetime | None, datetime | None] = (None, None)
    severity_assessment: IncidentSeverity = IncidentSeverity.MEDIUM


@dataclass(slots=True)
class KnowledgeChunkContext:
    id: UUID
    source_file: str
    chunk_index: int
    category: KnowledgeCategory | None
    content: str
    keywords: list[str] = field(default_factory=list)
    relevance_score: float | None = None


@dataclass(slots=True)
class EvidenceReference:
    source_type: str
    source_ref: str
    content: str
    relevance_score: float | None = None


@dataclass(slots=True)
class RootCauseResult:
    primary_cause: str
    contributing_factors: list[str] = field(default_factory=list)
    confidence_score: float | None = None
    reasoning_chain: str = ""
    evidence_refs: list[EvidenceReference] = field(default_factory=list)


@dataclass(slots=True)
class RemediationStepPlan:
    order: int
    action: str
    rationale: str | None = None
    risk_level: str = "LOW"
    command_hint: str | None = None
    is_automated: bool = False


@dataclass(slots=True)
class RemediationPlan:
    summary: str
    steps: list[RemediationStepPlan] = field(default_factory=list)


@dataclass(slots=True)
class TimelineEvent:
    timestamp: datetime
    event: str


@dataclass(slots=True)
class ReportResult:
    title: str
    executive_summary: str
    incident_summary: str
    root_cause_section: str
    evidence_section: str
    remediation_section: str
    timeline: list[TimelineEvent] = field(default_factory=list)
    format_version: str = "1.0"
    generated_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class StepExecution:
    step_name: str
    step_order: int
    status: InvestigationStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    output: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class AgentState:
    investigation_id: UUID
    incident_id: UUID
    incident_title: str
    raw_log: str
    incident_metadata: dict[str, Any] = field(default_factory=dict)
    incident_description: str | None = None
    service_name: str | None = None
    source: str | None = None
    environment: str | None = None
    log_signals: LogSignals | None = None
    knowledge_chunks: list[KnowledgeChunkContext] = field(default_factory=list)
    root_cause: RootCauseResult | None = None
    remediation: RemediationPlan | None = None
    report: ReportResult | None = None
    step_history: list[StepExecution] = field(default_factory=list)

    def to_report_payload(self) -> dict[str, Any]:
        if self.report is None:
            raise ValueError("Report has not been generated yet.")

        payload = asdict(self.report)
        payload["timeline"] = [
            {
                "timestamp": event["timestamp"].isoformat()
                if isinstance(event["timestamp"], datetime)
                else event["timestamp"],
                "event": event["event"],
            }
            for event in payload.get("timeline", [])
        ]
        payload["investigation_id"] = self.investigation_id
        payload["incident_id"] = self.incident_id
        return payload
