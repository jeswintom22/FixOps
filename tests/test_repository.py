import os
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from fixops.config import Settings
from fixops.db import Base, IncidentSeverity, IncidentStatus, InvestigationStatus, make_engine
from fixops.repository import (
    create_incident,
    create_investigation,
    create_or_update_report,
    get_incident,
    get_report_for_investigation,
    list_incidents,
    mark_investigation_completed,
    update_incident_status,
)


@pytest.fixture
async def db_session(tmp_path: Path) -> AsyncSession:
    os.environ["FIXOPS_DATA_DIR"] = str(tmp_path)
    os.environ["LLM_PROVIDER"] = "local"
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    engine = make_engine(str(settings.database_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    from sqlalchemy.ext.asyncio import async_sessionmaker

    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    async with session_factory() as session:
        yield session
    await engine.dispose()


async def test_create_and_fetch_incident(db_session: AsyncSession) -> None:
    incident = await create_incident(
        db_session,
        title="Test incident",
        raw_log="ERROR app timeout",
        severity=IncidentSeverity.HIGH,
    )
    fetched = await get_incident(db_session, incident.id)
    assert fetched is not None
    assert fetched.title == "Test incident"
    assert fetched.status == IncidentStatus.INVESTIGATING


async def test_list_incidents(db_session: AsyncSession) -> None:
    await create_incident(db_session, title="One", raw_log="error", severity=IncidentSeverity.LOW)
    await create_incident(db_session, title="Two", raw_log="error", severity=IncidentSeverity.LOW)
    incidents = await list_incidents(db_session, limit=10)
    assert len(incidents) == 2


async def test_investigation_lifecycle(db_session: AsyncSession) -> None:
    incident = await create_incident(db_session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM)
    investigation = await create_investigation(db_session, incident.id)
    completed = await mark_investigation_completed(db_session, investigation.id, confidence_score=0.85)
    assert completed.status == InvestigationStatus.COMPLETED
    assert completed.confidence_score == pytest.approx(0.85)


async def test_resolve_incident(db_session: AsyncSession) -> None:
    incident = await create_incident(db_session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM)
    resolved = await update_incident_status(db_session, incident.id, IncidentStatus.RESOLVED)
    assert resolved.status == IncidentStatus.RESOLVED


async def test_create_report(db_session: AsyncSession) -> None:
    from datetime import datetime, timezone

    incident = await create_incident(db_session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM)
    investigation = await create_investigation(db_session, incident.id)
    report_data = {
        "investigation_id": investigation.id,
        "incident_id": incident.id,
        "title": "Report",
        "executive_summary": "summary",
        "incident_summary": "summary",
        "root_cause_section": "rc",
        "evidence_section": "evidence",
        "remediation_section": "remediation",
        "timeline": [],
        "evidence_refs": [],
        "remediation_steps": [],
        "root_cause_retried": False,
        "remediation_retried": False,
        "confidence_score": 0.8,
        "format_version": "1.0",
        "generated_at": datetime.now(timezone.utc),
    }
    report = await create_or_update_report(db_session, report_data)
    fetched = await get_report_for_investigation(db_session, investigation.id)
    assert fetched is not None
    assert fetched.title == "Report"
