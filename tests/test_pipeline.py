import asyncio
from pathlib import Path
from uuid import uuid4

import pytest

from fixops.db import IncidentSeverity
from fixops.knowledge.loader import load_knowledge_base
from fixops.knowledge.retriever import KeywordRetriever
from fixops.llm.local import LocalLLMService
from fixops.pipeline import AgentOrchestrator
from fixops.pipeline.state import AgentState
from fixops.pipeline.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)


@pytest.fixture
def knowledge_dir(tmp_path: Path) -> Path:
    runbook_dir = tmp_path / "runbooks"
    runbook_dir.mkdir()
    (runbook_dir / "db_pool.md").write_text(
        "# DB Pool Runbook\n\n## Symptoms\nConnection timeouts.\n\n## Fix\nScale workers.",
        encoding="utf-8",
    )
    return tmp_path


@pytest.fixture
def retriever(knowledge_dir: Path) -> KeywordRetriever:
    return KeywordRetriever(load_knowledge_base(knowledge_dir))


async def _run(log: str, retriever: KeywordRetriever) -> AgentState:
    state = AgentState(
        investigation_id=uuid4(),
        incident_id=uuid4(),
        incident_title="Test incident",
        raw_log=log,
    )
    llm = LocalLLMService()
    orchestrator = AgentOrchestrator(
        steps=[
            LogAnalysisStep(llm),
            KnowledgeRetrievalStep(retriever),
            RootCauseAnalysisStep(llm),
            RemediationPlanningStep(llm),
            ReportGenerationStep(llm),
        ]
    )
    return await orchestrator.run(state)


def test_oomkilled_local_analysis(retriever: KeywordRetriever) -> None:
    log = "2026-01-01T00:00:00Z ERROR app OOMKilled exit code 137"
    state = asyncio.run(_run(log, retriever))
    assert state.log_signals is not None
    assert "OOM" in state.log_signals.error_type
    assert state.log_signals.severity_assessment == IncidentSeverity.HIGH
    assert state.report is not None
    assert state.root_cause is not None
    assert state.remediation is not None
    assert len(state.remediation.steps) >= 2


def test_database_pool_local_analysis(retriever: KeywordRetriever) -> None:
    log = (
        "2026-01-01T00:00:00Z ERROR svc HikariPool timeout\n"
        "2026-01-01T00:00:01Z ERROR svc SQLSTATE 53300 too many clients"
    )
    state = asyncio.run(_run(log, retriever))
    assert state.log_signals is not None
    assert "Database connection pool exhaustion" in state.log_signals.error_type
    assert state.report is not None
    assert "database connection pool exhaustion" in state.report.root_cause_section.lower()


def test_pipeline_captures_step_history(retriever: KeywordRetriever) -> None:
    log = "2026-01-01T00:00:00Z ERROR app timeout"
    state = asyncio.run(_run(log, retriever))
    step_names = {s.step_name for s in state.step_history}
    assert step_names == {
        "LOG_ANALYSIS",
        "KNOWLEDGE_RETRIEVAL",
        "ROOT_CAUSE_ANALYSIS",
        "REMEDIATION",
        "REPORT_GENERATION",
    }
    assert all(s.status.value == "COMPLETED" for s in state.step_history)
