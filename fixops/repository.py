from __future__ import annotations

import logging
import uuid
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from fixops.db import (
    Incident,
    IncidentSeverity,
    IncidentStatus,
    Investigation,
    InvestigationStatus,
    KnowledgeCategory,
    KnowledgeChunk,
    Report,
)

logger = logging.getLogger(__name__)


async def create_incident(
    session: AsyncSession,
    *,
    title: str,
    raw_log: str,
    description: str | None = None,
    severity: IncidentSeverity = IncidentSeverity.MEDIUM,
    source: str | None = None,
    service_name: str | None = None,
    environment: str | None = None,
    tags: Sequence[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Incident:
    incident = Incident(
        title=title,
        description=description,
        raw_log=raw_log,
        severity=severity,
        status=IncidentStatus.INVESTIGATING,
        source=source,
        service_name=service_name,
        environment=environment,
        tags=list(tags or []),
        metadata_=metadata or {},
    )
    session.add(incident)
    await session.commit()
    await session.refresh(incident)
    return incident


async def get_incident(session: AsyncSession, incident_id: uuid.UUID) -> Incident | None:
    return await session.get(Incident, incident_id)


async def list_incidents(
    session: AsyncSession,
    *,
    limit: int = 50,
    offset: int = 0,
) -> Sequence[Incident]:
    statement = select(Incident).order_by(desc(Incident.created_at)).limit(limit).offset(offset)
    result = await session.execute(statement)
    return result.scalars().all()


async def update_incident_status(
    session: AsyncSession,
    incident_id: uuid.UUID,
    status: IncidentStatus,
) -> Incident:
    incident = await session.get(Incident, incident_id)
    if incident is None:
        raise LookupError(f"Incident {incident_id} not found")
    incident.status = status
    incident.updated_at = datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(incident)
    return incident


async def create_investigation(
    session: AsyncSession,
    incident_id: uuid.UUID,
) -> Investigation:
    investigation = Investigation(
        incident_id=incident_id,
        status=InvestigationStatus.QUEUED,
    )
    session.add(investigation)
    await session.commit()
    await session.refresh(investigation)
    return investigation


async def get_investigation(
    session: AsyncSession, investigation_id: uuid.UUID
) -> Investigation | None:
    return await session.get(Investigation, investigation_id)


async def mark_investigation_running(
    session: AsyncSession,
    investigation_id: uuid.UUID,
) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError(f"Investigation {investigation_id} not found")
    investigation.status = InvestigationStatus.RUNNING
    investigation.started_at = investigation.started_at or datetime.now(timezone.utc)
    await session.commit()
    await session.refresh(investigation)
    return investigation


async def mark_investigation_completed(
    session: AsyncSession,
    investigation_id: uuid.UUID,
    confidence_score: float | None = None,
    root_cause_retried: bool = False,
    remediation_retried: bool = False,
) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError(f"Investigation {investigation_id} not found")
    investigation.status = InvestigationStatus.COMPLETED
    investigation.completed_at = datetime.now(timezone.utc)
    investigation.confidence_score = confidence_score
    investigation.root_cause_retried = root_cause_retried
    investigation.remediation_retried = remediation_retried
    investigation.current_step = None
    await session.commit()
    await session.refresh(investigation)
    return investigation


async def mark_investigation_failed(
    session: AsyncSession,
    investigation_id: uuid.UUID,
    error: str,
) -> Investigation:
    investigation = await session.get(Investigation, investigation_id)
    if investigation is None:
        raise LookupError(f"Investigation {investigation_id} not found")
    investigation.status = InvestigationStatus.FAILED
    investigation.error_message = error
    investigation.completed_at = datetime.now(timezone.utc)
    investigation.current_step = None
    await session.commit()
    await session.refresh(investigation)
    return investigation


async def create_or_update_report(
    session: AsyncSession,
    report_data: dict[str, Any],
) -> Report:
    investigation_id = report_data["investigation_id"]
    statement = select(Report).where(Report.investigation_id == investigation_id)
    result = await session.execute(statement)
    existing = result.scalar_one_or_none()

    if existing is None:
        report = Report(**report_data)
        session.add(report)
    else:
        for key, value in report_data.items():
            setattr(existing, key, value)
        report = existing
    await session.commit()
    await session.refresh(report)
    return report


async def get_report_for_investigation(
    session: AsyncSession,
    investigation_id: uuid.UUID,
) -> Report | None:
    statement = select(Report).where(Report.investigation_id == investigation_id)
    result = await session.execute(statement)
    return result.scalar_one_or_none()


async def get_report(session: AsyncSession, report_id: uuid.UUID) -> Report | None:
    return await session.get(Report, report_id)


async def save_knowledge_chunks(
    session: AsyncSession,
    chunks: Sequence[KnowledgeChunk],
) -> int:
    """Persist chunks, deleting any existing chunks from the same source_file set first."""
    source_files = {chunk.source_file for chunk in chunks}
    for source_file in source_files:
        statement = select(KnowledgeChunk).where(KnowledgeChunk.source_file == source_file)
        result = await session.execute(statement)
        for existing in result.scalars().all():
            await session.delete(existing)

    for chunk in chunks:
        session.add(chunk)

    await session.commit()
    return len(chunks)


async def list_knowledge_chunks(
    session: AsyncSession,
    category: KnowledgeCategory | None = None,
) -> Sequence[KnowledgeChunk]:
    statement = select(KnowledgeChunk)
    if category is not None:
        statement = statement.where(KnowledgeChunk.category == category)
    result = await session.execute(statement)
    return result.scalars().all()
