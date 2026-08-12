from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
from app.agent.steps import (
    KnowledgeRetrievalStep, LogAnalysisStep, RemediationPlanningStep,
    ReportGenerationStep, RootCauseAnalysisStep,
)
from app.api.deps import (
    get_agent_orchestrator,
    get_incident_service,
    get_investigation_service,
    get_report_service,
    get_session,
)
from app.config import get_settings
from app.core.constants import IncidentStatus
from app.core.logging import configure_logging
from app.db.session import AsyncSessionLocal, close_db, init_db
from app.models.incident import Incident
from app.models.report import Report
from app.schemas import (
    IncidentCreate,
    IncidentRead,
    InvestigationRead,
    InvestigationRunRequest,
    InvestigationRunResponse,
    ReportRead,
    StepExecutionRead,
)
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService
from app.services.ai_factory import build_embedding_provider, build_llm_provider
from app.services.db_knowledge_service import DBKnowledgeService
from app.services.mock_knowledge_service import MockKnowledgeService

logger = logging.getLogger(__name__)
_investigate_requests: dict[str, list[float]] = {}

@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    configure_logging(get_settings().log_level)
    await init_db()
    try:
        yield
    finally:
        await close_db()


app = FastAPI(
    title="FixOps IQ API",
    version="0.4.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def require_write_auth(x_api_key: str | None = Header(default=None)) -> None:
    configured = get_settings().api_auth_token
    if configured and x_api_key != configured:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing API key.")


async def investigate_rate_limit(request: Request) -> None:
    now = time.monotonic()
    key = request.client.host if request.client else "unknown"
    recent = [stamp for stamp in _investigate_requests.get(key, []) if now - stamp < 60]
    if len(recent) >= 10:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Investigation rate limit exceeded.")
    recent.append(now)
    _investigate_requests[key] = recent


async def run_investigation_job(investigation_id: UUID) -> None:
    async with AsyncSessionLocal() as session:
        incident_service = IncidentService(session=session)
        investigation_service = InvestigationService(session=session)
        report_service = ReportService(session=session)
        settings = get_settings()
        llm_service = build_llm_provider(settings)
        embedding_service = build_embedding_provider(settings)
        knowledge_service = (
            MockKnowledgeService()
            if settings.resolved_ai_provider == "mock"
            else DBKnowledgeService(session=session, embedding_service=embedding_service)
        )
        orchestrator = AgentOrchestrator(
            steps=[
                LogAnalysisStep(llm_service=llm_service),
                KnowledgeRetrievalStep(embedding_service=embedding_service, knowledge_service=knowledge_service),
                RootCauseAnalysisStep(llm_service=llm_service),
                RemediationPlanningStep(llm_service=llm_service),
                ReportGenerationStep(llm_service=llm_service),
            ],
            incident_service=incident_service,
            investigation_service=investigation_service,
            report_service=report_service,
        )
        try:
            await orchestrator.run(investigation_id)
        except Exception:
            logger.exception("Investigation job failed", extra={"investigation_id": investigation_id})


def error_response(
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
            }
        },
    )


@app.exception_handler(RequestValidationError)
async def handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
    return error_response(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        code="validation_error",
        message=str(exc),
    )


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled application error")
    return error_response(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        code="internal_error",
        message="An unexpected internal error occurred.",
    )


@app.post(
    "/incidents",
    response_model=IncidentRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_incident(
    payload: IncidentCreate,
    incident_service: IncidentService = Depends(get_incident_service),
    _: None = Depends(require_write_auth),
) -> Incident:
    return await incident_service.create(payload.model_dump(by_alias=False))


@app.post(
    "/investigate",
    response_model=InvestigationRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
async def investigate_incident(
    payload: InvestigationRunRequest,
    background_tasks: BackgroundTasks,
    incident_service: IncidentService = Depends(get_incident_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
    _: None = Depends(require_write_auth),
    __: None = Depends(investigate_rate_limit),
) -> InvestigationRunResponse:
    incident = await incident_service.get_by_id(payload.incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {payload.incident_id} was not found.",
        )
    await incident_service.update_status(
        incident_id=payload.incident_id,
        status=IncidentStatus.INVESTIGATING,
    )
    try:
        investigation = await investigation_service.create({"incident_id": payload.incident_id})
    except IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="An active investigation already exists for this incident.") from exc
    background_tasks.add_task(run_investigation_job, investigation.id)

    return InvestigationRunResponse(
        investigation=investigation,
        report_id=None,
    )


@app.get("/investigations/{id}", response_model=InvestigationRead)
async def get_investigation(id: UUID, investigation_service: InvestigationService = Depends(get_investigation_service)) -> object:
    investigation = await investigation_service.get_by_id(id)
    if investigation is None:
        raise HTTPException(status_code=404, detail=f"Investigation {id} was not found.")
    return investigation


@app.get("/investigations/{id}/steps", response_model=list[StepExecutionRead])
async def get_investigation_steps(id: UUID, investigation_service: InvestigationService = Depends(get_investigation_service)) -> list[object]:
    if await investigation_service.get_by_id(id) is None:
        raise HTTPException(status_code=404, detail=f"Investigation {id} was not found.")
    return await investigation_service.get_steps(id)


@app.get("/healthz", status_code=status.HTTP_200_OK)
async def healthcheck(session: AsyncSession = Depends(get_session)) -> dict[str, str]:
    await session.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/reports/{id}", response_model=ReportRead)
async def get_report(
    id: UUID,
    report_service: ReportService = Depends(get_report_service),
) -> Report:
    report = await report_service.get_by_id(id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Report {id} was not found.",
        )
    return report


@app.get("/investigations/{id}/report", response_model=ReportRead)
async def get_investigation_report(id: UUID, report_service: ReportService = Depends(get_report_service)) -> Report:
    report = await report_service.get_by_investigation(id)
    if report is None:
        raise HTTPException(status_code=404, detail=f"Report for investigation {id} was not found.")
    return report
