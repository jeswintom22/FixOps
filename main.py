from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import AsyncIterator
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.agent.orchestrator import AgentOrchestrator
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
from app.db.session import close_db, init_db
from app.models.incident import Incident
from app.models.report import Report
from app.schemas import (
    IncidentCreate,
    IncidentRead,
    InvestigationRead,
    InvestigationRunRequest,
    InvestigationRunResponse,
    ReportRead,
)
from app.services.incident_service import IncidentService
from app.services.investigation_service import InvestigationService
from app.services.report_service import ReportService

logger = logging.getLogger(__name__)

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
) -> Incident:
    return await incident_service.create(payload.model_dump(by_alias=False))


@app.post(
    "/investigate",
    response_model=InvestigationRunResponse,
    status_code=status.HTTP_201_CREATED,
)
async def investigate_incident(
    payload: InvestigationRunRequest,
    incident_service: IncidentService = Depends(get_incident_service),
    investigation_service: InvestigationService = Depends(get_investigation_service),
    report_service: ReportService = Depends(get_report_service),
    orchestrator: AgentOrchestrator = Depends(get_agent_orchestrator),
) -> InvestigationRunResponse:
    incident = await incident_service.get_by_id(payload.incident_id)
    if incident is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident {payload.incident_id} was not found.",
        )
    active_investigation = await investigation_service.get_active_by_incident_id(payload.incident_id)
    if active_investigation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                f"Incident {payload.incident_id} already has an active investigation "
                f"({active_investigation.id})."
            ),
        )

    await incident_service.update_status(
        incident_id=payload.incident_id,
        status=IncidentStatus.INVESTIGATING,
    )
    investigation = await investigation_service.create({"incident_id": payload.incident_id})

    try:
        await orchestrator.run(investigation.id)
    except LookupError as exc:
        await incident_service.update_status(
            incident_id=payload.incident_id,
            status=IncidentStatus.OPEN,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except ValueError as exc:
        await incident_service.update_status(
            incident_id=payload.incident_id,
            status=IncidentStatus.OPEN,
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except Exception:
        await incident_service.update_status(
            incident_id=payload.incident_id,
            status=IncidentStatus.OPEN,
        )
        raise

    refreshed = await investigation_service.get_by_id(investigation.id)
    report = await report_service.get_by_investigation(investigation.id)
    if refreshed is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Investigation was created but could not be reloaded.",
        )

    return InvestigationRunResponse(
        investigation=refreshed,
        report_id=report.id if report is not None else None,
    )


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
