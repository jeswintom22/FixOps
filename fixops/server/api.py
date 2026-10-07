from __future__ import annotations

import logging
import secrets
import uuid
from collections.abc import AsyncIterator, Sequence
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from fixops.config import get_settings
from fixops.db import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    Investigation,
    InvestigationStatus,
    Report,
    get_session,
    init_db,
    make_engine,
)
from fixops.knowledge.loader import KnowledgeChunk as LoaderChunk
from fixops.knowledge.loader import load_knowledge_base
from fixops.knowledge.retriever import KeywordRetriever
from fixops.llm.providers import build_llm_service
from fixops.pipeline import AgentOrchestrator
from fixops.pipeline.state import AgentState
from fixops.pipeline.steps import (
    KnowledgeRetrievalStep,
    LogAnalysisStep,
    RemediationPlanningStep,
    ReportGenerationStep,
    RootCauseAnalysisStep,
)
from fixops.repository import (
    create_incident,
    create_investigation,
    create_or_update_report,
    get_incident,
    get_report,
    get_report_for_investigation,
    list_incidents,
    mark_investigation_completed,
    mark_investigation_failed,
    mark_investigation_running,
    update_incident_status,
)
from fixops.security.redaction import redact

logger = logging.getLogger(__name__)


class IncidentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    raw_log: str = Field(min_length=1, max_length=50000)
    severity: str = "MEDIUM"
    source: str | None = None
    service_name: str | None = None
    environment: str | None = None
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, str] = Field(default_factory=dict)


class IncidentRead(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None = None
    raw_log: str
    severity: str
    status: str
    source: str | None = None
    service_name: str | None = None
    environment: str | None = None
    tags: list[str]
    metadata_: dict[str, Any] = Field(serialization_alias="metadata")
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
        populate_by_name = True


class InvestigationRunRequest(BaseModel):
    incident_id: uuid.UUID


class InvestigationRead(BaseModel):
    id: uuid.UUID
    incident_id: uuid.UUID
    status: str
    current_step: str | None = None
    error_message: str | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    root_cause_retried: bool
    remediation_retried: bool
    confidence_score: float | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class InvestigationRunResponse(BaseModel):
    investigation: InvestigationRead
    report_id: uuid.UUID | None = None


class ReportRead(BaseModel):
    id: uuid.UUID
    investigation_id: uuid.UUID
    incident_id: uuid.UUID
    title: str
    executive_summary: str
    incident_summary: str
    root_cause_section: str
    evidence_section: str
    remediation_section: str
    timeline: list[dict[str, Any]]
    evidence_refs: list[dict[str, Any]]
    remediation_steps: list[dict[str, Any]]
    root_cause_retried: bool
    remediation_retried: bool
    confidence_score: float | None = None
    format_version: str
    generated_at: datetime

    class Config:
        from_attributes = True


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    await init_db()
    await _mark_stale_investigations_failed()
    yield


app = FastAPI(
    title="FixOps API",
    version="0.5.0",
    lifespan=lifespan,
)

_origins: list[str] = []
if get_settings().cors_origins:
    _origins = [origin.strip() for origin in get_settings().cors_origins if origin.strip()]
if not _origins:
    _origins = ["http://localhost:3000", "http://localhost:8501"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


async def require_auth(x_api_key: str | None = Header(default=None)) -> None:
    configured = get_settings().api_auth_token
    if not configured:
        return
    if x_api_key is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing API key.")
    if not secrets.compare_digest(x_api_key, configured):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API key.")


async def get_db() -> AsyncIterator[AsyncSession]:
    async for session in get_session():
        yield session


async def _mark_stale_investigations_failed() -> None:
    settings = get_settings()
    engine = make_engine(str(settings.database_path))
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        statement = select(Investigation).where(
            Investigation.status.in_([InvestigationStatus.QUEUED, InvestigationStatus.RUNNING])
        )
        result = await session.execute(statement)
        for investigation in result.scalars().all():
            investigation.status = InvestigationStatus.FAILED
            investigation.error_message = "Server restarted while investigation was in progress."
            investigation.completed_at = datetime.now(timezone.utc)
            investigation.current_step = None
        await session.commit()
    await engine.dispose()


async def _load_retriever(session: AsyncSession) -> KeywordRetriever:
    from fixops.repository import list_knowledge_chunks

    db_chunks = await list_knowledge_chunks(session)
    if not db_chunks:
        chunks = load_knowledge_base(Path(__file__).resolve().parents[2] / "knowledge_base")
    else:
        chunks = [
            LoaderChunk(
                source_file=chunk.source_file,
                chunk_index=chunk.chunk_index,
                category=chunk.category,
                content=chunk.content,
                keywords=list(chunk.keywords),
            )
            for chunk in db_chunks
        ]
    return KeywordRetriever(chunks)


async def _run_investigation_job(investigation_id: uuid.UUID) -> None:
    settings = get_settings()
    engine = make_engine(str(settings.database_path))
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        investigation = await session.get(Investigation, investigation_id)
        if investigation is None:
            logger.error("Investigation %s not found", investigation_id)
            await engine.dispose()
            return

        incident = await session.get(Incident, investigation.incident_id)
        if incident is None:
            await mark_investigation_failed(session, investigation_id, "Incident not found")
            await engine.dispose()
            return

        await mark_investigation_running(session, investigation_id)

        llm_service = build_llm_service(settings)
        retriever = await _load_retriever(session)
        orchestrator = AgentOrchestrator(
            steps=[
                LogAnalysisStep(llm_service=llm_service),
                KnowledgeRetrievalStep(retriever=retriever),
                RootCauseAnalysisStep(llm_service=llm_service),
                RemediationPlanningStep(llm_service=llm_service),
                ReportGenerationStep(llm_service=llm_service),
            ]
        )

        raw_log = incident.raw_log
        if settings.redaction_enabled:
            raw_log = redact(raw_log)

        state = AgentState(
            investigation_id=investigation.id,
            incident_id=incident.id,
            incident_title=incident.title,
            raw_log=raw_log,
            incident_description=incident.description,
            incident_metadata=dict(incident.metadata_),
            service_name=incident.service_name,
            source=incident.source,
            environment=incident.environment,
        )

        try:
            final_state = await orchestrator.run(state)
        except Exception as exc:
            logger.exception("Investigation failed")
            await mark_investigation_failed(session, investigation_id, str(exc))
            await engine.dispose()
            return

        if final_state.report is None:
            await mark_investigation_failed(session, investigation_id, "No report generated")
            await engine.dispose()
            return

        report_data = final_state.to_report_payload()
        await create_or_update_report(session, report_data)
        await mark_investigation_completed(
            session,
            investigation_id,
            confidence_score=final_state.root_cause.confidence_score
            if final_state.root_cause
            else None,
            root_cause_retried=final_state.root_cause_retried,
            remediation_retried=final_state.remediation_retried,
        )
        await update_incident_status(session, incident.id, IncidentStatus.ANALYZED)
    await engine.dispose()


@app.post("/incidents", response_model=IncidentRead, status_code=status.HTTP_201_CREATED)
async def api_create_incident(
    payload: IncidentCreate,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
) -> Incident:
    raw_log = payload.raw_log
    if get_settings().redaction_enabled:
        raw_log = redact(raw_log)
    try:
        severity = IncidentSeverity(payload.severity.upper())
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail=f"Invalid severity: {payload.severity}"
        ) from exc
    return await create_incident(
        session,
        title=payload.title,
        description=payload.description,
        raw_log=raw_log,
        severity=severity,
        source=payload.source,
        service_name=payload.service_name,
        environment=payload.environment,
        tags=payload.tags,
        metadata=payload.metadata,
    )


@app.post(
    "/investigate", response_model=InvestigationRunResponse, status_code=status.HTTP_202_ACCEPTED
)
async def api_investigate(
    payload: InvestigationRunRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
) -> InvestigationRunResponse:
    incident = await get_incident(session, payload.incident_id)
    if incident is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")
    await update_incident_status(session, incident.id, IncidentStatus.INVESTIGATING)
    investigation = await create_investigation(session, incident.id)
    background_tasks.add_task(_run_investigation_job, investigation.id)
    return InvestigationRunResponse(investigation=investigation, report_id=None)


@app.get("/incidents", response_model=list[IncidentRead])
async def api_list_incidents(
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
    limit: int = 50,
) -> Sequence[Incident]:
    return await list_incidents(session, limit=limit)


@app.get("/investigations/{investigation_id}", response_model=InvestigationRead)
async def api_get_investigation(
    investigation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Investigation not found")
    return investigation


@app.get("/investigations/{investigation_id}/report", response_model=ReportRead)
async def api_get_investigation_report(
    investigation_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
) -> Report:
    report = await get_report_for_investigation(session, investigation_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@app.get("/reports/{report_id}", response_model=ReportRead)
async def api_get_report(
    report_id: uuid.UUID,
    session: AsyncSession = Depends(get_db),
    _: None = Depends(require_auth),
) -> Report:
    report = await get_report(session, report_id)
    if report is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    return report


@app.get("/healthz")
async def healthcheck(session: AsyncSession = Depends(get_db)) -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(Exception)
async def handle_unexpected_error(_: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API error")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"error": {"code": "internal_error", "message": "An unexpected error occurred."}},
    )
