from __future__ import annotations

from collections.abc import AsyncIterator

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.agent.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)
from app.config import get_settings
from app.db.session import get_db_session
from app.services import (
    DBKnowledgeService,
    EmbeddingService,
    IncidentService,
    InvestigationService,
    LLMService,
    MockKnowledgeService,
    ReportService,
)
from app.services.ai_factory import get_embedding_service, get_llm_service
from app.services.knowledge_service import KnowledgeService


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


def get_knowledge_service(
    session: AsyncSession = Depends(get_session),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
) -> KnowledgeService:
    if get_settings().resolved_ai_provider == "mock":
        return MockKnowledgeService()
    return DBKnowledgeService(session=session, embedding_service=embedding_service)


def get_incident_service(session: AsyncSession = Depends(get_session)) -> IncidentService:
    return IncidentService(session=session)


def get_investigation_service(
    session: AsyncSession = Depends(get_session),
) -> InvestigationService:
    return InvestigationService(session=session)


def get_report_service(session: AsyncSession = Depends(get_session)) -> ReportService:
    return ReportService(session=session)


def get_agent_orchestrator(
    incident_service: IncidentService = Depends(get_incident_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
    report_service: ReportService = Depends(get_report_service),
    llm_service: LLMService = Depends(get_llm_service),
    embedding_service: EmbeddingService = Depends(get_embedding_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> AgentOrchestrator:
    return AgentOrchestrator(
        steps=[
            LogAnalysisStep(llm_service=llm_service),
            KnowledgeRetrievalStep(
                embedding_service=embedding_service,
                knowledge_service=knowledge_service,
            ),
            RootCauseAnalysisStep(llm_service=llm_service),
            RemediationPlanningStep(llm_service=llm_service),
            ReportGenerationStep(llm_service=llm_service),
        ],
        incident_service=incident_service,
        investigation_service=investigation_service,
        report_service=report_service,
    )
