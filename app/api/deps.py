from __future__ import annotations

from collections.abc import AsyncIterator
from functools import lru_cache

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
from app.db.session import get_db_session
from app.config import get_settings
from app.services import (
    AzureOpenAIService,
    IncidentService,
    InvestigationService,
    MockKnowledgeService,
    ReportService,
)
from app.services.azure_ai_service import AzureAIService
from app.services.knowledge_service import KnowledgeService


async def get_session() -> AsyncIterator[AsyncSession]:
    async for session in get_db_session():
        yield session


@lru_cache
def get_azure_ai_service() -> AzureAIService:
    return AzureOpenAIService.from_settings(get_settings())


@lru_cache
def get_knowledge_service() -> KnowledgeService:
    return MockKnowledgeService()


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
    azure_ai_service: AzureAIService = Depends(get_azure_ai_service),
    knowledge_service: KnowledgeService = Depends(get_knowledge_service),
) -> AgentOrchestrator:
    return AgentOrchestrator(
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
