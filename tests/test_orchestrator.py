import asyncio
import pytest

from app.agent.orchestrator import AgentOrchestrator
from app.agent.steps import (
    KnowledgeRetrievalStep, LogAnalysisStep, RemediationPlanningStep,
    ReportGenerationStep, RootCauseAnalysisStep,
)
from app.services import MockAIService, MockKnowledgeService
from scripts.demo_run import (
    InMemoryIncidentService, InMemoryInvestigationService, InMemoryReportService,
    seed_sample_data,
)


def build_orchestrator(incident, investigation, ai=None, incident_service=None, investigation_service=None):
    ai = ai or MockAIService()
    return AgentOrchestrator(
        steps=[
            LogAnalysisStep(llm_service=ai),
            KnowledgeRetrievalStep(embedding_service=ai, knowledge_service=MockKnowledgeService()),
            RootCauseAnalysisStep(llm_service=ai),
            RemediationPlanningStep(llm_service=ai),
            ReportGenerationStep(llm_service=ai),
        ],
        incident_service=incident_service or InMemoryIncidentService({incident.id: incident}),
        investigation_service=investigation_service or InMemoryInvestigationService({investigation.id: investigation}),
        report_service=InMemoryReportService(),
    )


def test_mock_orchestrator_persists_structured_output():
    incident, investigation = seed_sample_data()
    state = asyncio.run(build_orchestrator(incident, investigation).run(investigation.id))
    assert state.root_cause and state.root_cause.evidence_refs
    assert state.remediation and len(state.remediation.steps) >= 2
    assert state.to_report_payload()["evidence_refs"]


def test_step_failure_marks_investigation_failed():
    incident, investigation = seed_sample_data()

    class FailingAI(MockAIService):
        async def structured_complete(self, prompt, schema):
            if schema.__name__ == "RootCauseResponse":
                raise RuntimeError("provider unavailable")
            return await super().structured_complete(prompt, schema)

    service = InMemoryInvestigationService({investigation.id: investigation})
    with pytest.raises(RuntimeError, match="provider unavailable"):
        asyncio.run(build_orchestrator(incident, investigation, ai=FailingAI(), investigation_service=service).run(investigation.id))
    assert investigation.error_message == "provider unavailable"
