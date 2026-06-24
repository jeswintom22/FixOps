from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import Field

from app.core.constants import IncidentSeverity
from app.schemas.common import ORMModel


class TimeWindow(ORMModel):
    start: datetime
    end: datetime


class ProviderProvenance(ORMModel):
    provider_name: str
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source: str | None = None


from app.context.types.provider_types import ContextSection


class ProviderContext(ORMModel):
    section_name: ContextSection
    payload: LogContext | MetricContext | MemoryContext | VerificationContext | dict[str, Any] = Field(default_factory=dict)
    provenance: ProviderProvenance
    confidence: float | None = None


class LogSnippet(ORMModel):
    snippet: str
    timestamp: datetime
    source: str
    severity_tag: str | None = None
    provenance: ProviderProvenance | None = None


class LogContext(ORMModel):
    top_snippets: list[LogSnippet] = Field(default_factory=list)
    error_count: int = 0
    trace_links: list[str] = Field(default_factory=list)


class MetricEntry(ORMModel):
    name: str
    baseline: float | None = None
    current: float | None = None
    delta_pct: float | None = None
    trend: str | None = None
    provenance: ProviderProvenance | None = None


class SLOViolation(ORMModel):
    metric_name: str
    threshold: str
    current_value: float
    provenance: ProviderProvenance | None = None


class MetricContext(ORMModel):
    key_metrics: list[MetricEntry] = Field(default_factory=list)
    slo_violations: list[SLOViolation] = Field(default_factory=list)


class MemoryIncidentReference(ORMModel):
    incident_id: UUID
    title: str
    summary_snippet: str
    similarity_score: float | None = None
    provenance: ProviderProvenance | None = None


class KnowledgeEntryContext(ORMModel):
    id: UUID
    type: str
    content: str
    confidence: float | None = None
    similarity_score: float | None = None
    provenance: ProviderProvenance | None = None


class RunbookContext(ORMModel):
    id: UUID
    title: str
    excerpt: str
    relevance_score: float | None = None
    provenance: ProviderProvenance | None = None


class MemoryContext(ORMModel):
    related_incidents: list[MemoryIncidentReference] = Field(default_factory=list)
    knowledge_entries: list[KnowledgeEntryContext] = Field(default_factory=list)
    applicable_runbooks: list[RunbookContext] = Field(default_factory=list)


class VerificationContext(ORMModel):
    verification_status: str
    evidence_summary: list[str] = Field(default_factory=list)


class ConfidenceSummary(ORMModel):
    overall_confidence: float | None = None
    notes: str | None = None


class ProviderStatus(ORMModel):
    provider_name: str
    section: ContextSection
    status: str
    message: str | None = None
    trace_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class IncidentContext(ORMModel):
    incident_id: UUID
    trace_id: str
    generated_at: datetime = Field(default_factory=datetime.utcnow)
    summary: str
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    service_name: str | None = None
    environment: str | None = None
    time_window: TimeWindow | None = None
    flags: list[str] = Field(default_factory=list)
    confidence_summary: ConfidenceSummary = Field(default_factory=ConfidenceSummary)
    providers_used: list[str] = Field(default_factory=list)
    provenance: list[ProviderProvenance] = Field(default_factory=list)
    provider_diagnostics: list[ProviderStatus] = Field(default_factory=list)
    logs: LogContext | None = None
    metrics: MetricContext | None = None
    memory: MemoryContext | None = None
    verification: VerificationContext | None = None
