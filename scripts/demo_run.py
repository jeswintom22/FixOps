from __future__ import annotations

import asyncio
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.agent.orchestrator import AgentOrchestrator
from app.agent.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)
from app.core.constants import (
    DeploymentEnvironment,
    IncidentSeverity,
    IncidentStatus,
    InvestigationStatus,
)
from app.models.incident import Incident
from app.models.investigation import Investigation
from app.models.report import Report
from app.services import MockAzureAIService, MockKnowledgeService


async def main() -> None:
    incident, investigation = seed_sample_data()

    incident_service = InMemoryIncidentService({incident.id: incident})
    investigation_service = InMemoryInvestigationService({investigation.id: investigation})
    report_service = InMemoryReportService()
    azure_ai_service = MockAzureAIService()
    knowledge_service = MockKnowledgeService()

    orchestrator = AgentOrchestrator(
        steps=[
            LogAnalysisStep(azure_ai_service=azure_ai_service),
            KnowledgeRetrievalStep(
                azure_ai_service=azure_ai_service,
                knowledge_service=knowledge_service,
            ),
            RootCauseAnalysisStep(azure_ai_service=azure_ai_service),
            RemediationPlanningStep(azure_ai_service=azure_ai_service),
            ReportGenerationStep(azure_ai_service=azure_ai_service),
        ],
        incident_service=incident_service,
        investigation_service=investigation_service,
        report_service=report_service,
    )

    state = await orchestrator.run(investigation.id)

    print("Incident Summary")
    print(state.report.incident_summary if state.report is not None else incident.description)
    print()

    print("Root Cause")
    print(state.root_cause.primary_cause if state.root_cause is not None else "Unavailable")
    print()

    print("Evidence")
    for evidence in state.root_cause.evidence_refs if state.root_cause is not None else []:
        print(
            f"- [{evidence.source_type}] {evidence.source_ref}: "
            f"{evidence.content}"
        )
    print()

    print("Remediation Plan")
    if state.remediation is not None:
        print(state.remediation.summary)
        for step in state.remediation.steps:
            command = f" | Command: {step.command_hint}" if step.command_hint else ""
            print(f"{step.order}. {step.action}{command}")
    else:
        print("Unavailable")
    print()

    print("Final Report")
    if state.report is not None:
        print(state.report.title)
        print()
        print(state.report.executive_summary)
        print()
        print("Root Cause Section")
        print(state.report.root_cause_section)
        print()
        print("Evidence Section")
        print(state.report.evidence_section)
        print()
        print("Remediation Section")
        print(state.report.remediation_section)
    else:
        print("Unavailable")


def seed_sample_data() -> tuple[Incident, Investigation]:
    incident = Incident(
        id=uuid4(),
        title="Payments checkout spike causing transaction timeouts",
        description=(
            "Checkout requests started timing out in production after a traffic spike "
            "during the morning campaign window."
        ),
        raw_log="\n".join(
            [
                "2026-06-11T09:14:03Z INFO payments-api checkout latency p95 crossed 4200ms region=ap-south-1",
                "2026-06-11T09:16:18Z ERROR payments-api com.zaxxer.hikari.pool.HikariPool Connection is not available, request timed out after 30000ms",
                "2026-06-11T09:16:21Z ERROR payments-api org.postgresql.util.PSQLException FATAL: sorry, too many clients already SQLSTATE 53300",
                "2026-06-11T09:18:07Z WARN payments-api retry storm detected for authorize-payment requests trace=8d0c1",
                "2026-06-11T09:20:11Z WARN payments-api readiness probe failed while inflight requests remained above threshold",
            ]
        ),
        severity=IncidentSeverity.HIGH,
        status=IncidentStatus.INVESTIGATING,
        source="demo_run",
        service_name="payments-api",
        environment=DeploymentEnvironment.PROD,
        tags=["payments", "database", "checkout"],
        metadata_={
            "cluster": "prod-ap-south-1",
            "campaign": "mid-year-sale",
            "region": "ap-south-1",
        },
    )
    investigation = Investigation(
        id=uuid4(),
        incident_id=incident.id,
    )
    return incident, investigation


@dataclass(slots=True)
class InMemoryIncidentService:
    incidents: dict[UUID, Incident]

    async def get_by_id(self, incident_id: UUID) -> Incident | None:
        return self.incidents.get(incident_id)

    async def update_status(self, incident_id: UUID, status: IncidentStatus) -> Incident:
        incident = self.incidents.get(incident_id)
        if incident is None:
            raise LookupError(f"Incident {incident_id} was not found.")

        incident.status = status
        incident.updated_at = datetime.now(UTC)
        return incident


@dataclass(slots=True)
class InMemoryInvestigationService:
    investigations: dict[UUID, Investigation]
    step_outputs: dict[UUID, dict[str, dict[str, object]]] = field(default_factory=dict)

    async def get_by_id(self, investigation_id: UUID) -> Investigation | None:
        return self.investigations.get(investigation_id)

    async def mark_running(self, investigation_id: UUID) -> Investigation:
        investigation = await self._require(investigation_id)
        investigation.status = InvestigationStatus.RUNNING
        investigation.started_at = investigation.started_at or datetime.now(UTC)
        return investigation

    async def mark_step_started(self, investigation_id: UUID, step_name: str) -> Investigation:
        investigation = await self._require(investigation_id)
        investigation.current_step = step_name
        return investigation

    async def record_step_completion(
        self,
        investigation_id: UUID,
        step_name: str,
        step_order: int,
        output: dict[str, object],
    ) -> Investigation:
        investigation = await self._require(investigation_id)
        investigation.current_step = step_name
        self.step_outputs.setdefault(investigation_id, {})[step_name] = {
            "order": step_order,
            "output": output,
        }
        return investigation

    async def mark_completed(self, investigation_id: UUID) -> Investigation:
        investigation = await self._require(investigation_id)
        investigation.status = InvestigationStatus.COMPLETED
        investigation.completed_at = datetime.now(UTC)
        return investigation

    async def mark_failed(self, investigation_id: UUID, error: str) -> Investigation:
        investigation = await self._require(investigation_id)
        investigation.status = InvestigationStatus.FAILED
        investigation.error_message = error
        return investigation

    async def _require(self, investigation_id: UUID) -> Investigation:
        investigation = await self.get_by_id(investigation_id)
        if investigation is None:
            raise LookupError(f"Investigation {investigation_id} was not found.")
        return investigation


@dataclass(slots=True)
class InMemoryReportService:
    reports_by_investigation: dict[UUID, Report] = field(default_factory=dict)

    async def create(self, investigation_id: UUID, report_data: dict[str, object]) -> Report:
        report = Report(
            id=uuid4(),
            **report_data,
        )
        self.reports_by_investigation[investigation_id] = report
        return report


if __name__ == "__main__":
    asyncio.run(main())
