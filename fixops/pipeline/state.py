from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from fixops.db import IncidentSeverity, InvestigationStatus


@dataclass
class LogSignals:
    error_type: str
    affected_service: str | None
    key_terms: list[str] = field(default_factory=list)
    anomaly_signals: list[str] = field(default_factory=list)
    timestamp_range: tuple[datetime | None, datetime | None] = (None, None)
    severity_assessment: IncidentSeverity = IncidentSeverity.MEDIUM


@dataclass
class KnowledgeChunkContext:
    source_file: str
    chunk_index: int
    category: str | None
    content: str
    keywords: list[str] = field(default_factory=list)
    relevance_score: float | None = None


@dataclass
class EvidenceReference:
    source_type: str
    source_ref: str
    content: str
    relevance_score: float | None = None


@dataclass
class RootCauseResult:
    primary_cause: str
    contributing_factors: list[str] = field(default_factory=list)
    confidence_score: float | None = None
    reasoning_chain: str = ""
    evidence_refs: list[EvidenceReference] = field(default_factory=list)


@dataclass
class RemediationStepPlan:
    order: int
    action: str
    rationale: str | None = None
    risk_level: str = "LOW"
    command_hint: str | None = None
    is_automated: bool = False


@dataclass
class RemediationPlan:
    summary: str
    steps: list[RemediationStepPlan] = field(default_factory=list)


@dataclass
class TimelineEvent:
    timestamp: datetime
    event: str


@dataclass
class ReportResult:
    title: str
    executive_summary: str
    incident_summary: str
    root_cause_section: str
    evidence_section: str
    remediation_section: str
    timeline: list[TimelineEvent] = field(default_factory=list)
    format_version: str = "1.0"
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class StepExecution:
    step_name: str
    step_order: int
    status: InvestigationStatus
    started_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    output: dict[str, Any] = field(default_factory=dict)


@dataclass
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
    root_cause_retried: bool = False
    remediation: RemediationPlan | None = None
    remediation_retried: bool = False
    report: ReportResult | None = None
    step_history: list[StepExecution] = field(default_factory=list)

    def to_report_payload(self) -> dict[str, Any]:
        if self.report is None:
            raise ValueError("Report has not been generated yet")

        return {
            "investigation_id": self.investigation_id,
            "incident_id": self.incident_id,
            "title": self.report.title,
            "executive_summary": self.report.executive_summary,
            "incident_summary": self.report.incident_summary,
            "root_cause_section": self.report.root_cause_section,
            "evidence_section": self.report.evidence_section,
            "remediation_section": self.report.remediation_section,
            "timeline": [
                {"timestamp": event.timestamp, "event": event.event}
                for event in self.report.timeline
            ],
            "evidence_refs": [
                {
                    "source_type": ref.source_type,
                    "source_ref": ref.source_ref,
                    "content": ref.content,
                    "relevance_score": ref.relevance_score,
                }
                for ref in (self.root_cause.evidence_refs if self.root_cause else [])
            ],
            "remediation_steps": [
                {
                    "order": step.order,
                    "action": step.action,
                    "rationale": step.rationale,
                    "risk_level": step.risk_level,
                    "command_hint": step.command_hint,
                    "is_automated": step.is_automated,
                }
                for step in (self.remediation.steps if self.remediation else [])
            ],
            "root_cause_retried": self.root_cause_retried,
            "remediation_retried": self.remediation_retried,
            "confidence_score": self.root_cause.confidence_score if self.root_cause else None,
            "format_version": self.report.format_version,
            "generated_at": self.report.generated_at,
        }
