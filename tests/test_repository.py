import asyncio
import os
from datetime import datetime, timezone
from pathlib import Path

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

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


def _settings_for(tmp_path: Path) -> Settings:
    os.environ["FIXOPS_DATA_DIR"] = str(tmp_path)
    os.environ["LLM_PROVIDER"] = "local"
    settings = Settings()
    settings.data_dir.mkdir(parents=True, exist_ok=True)
    return settings


async def _run_in_isolated_session(
    tmp_path: Path, test_logic: callable
) -> None:
    """Create a temporary DB/session and run async test logic in a single loop."""
    settings = _settings_for(tmp_path)
    engine = make_engine(str(settings.database_path))

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    session_factory = async_sessionmaker(
        bind=engine, class_=AsyncSession, expire_on_commit=False
    )
    session = session_factory()
    try:
        await test_logic(session)
    finally:
        await session.close()
        await engine.dispose()


def test_create_and_fetch_incident(tmp_path: Path) -> None:
    async def _logic(session: AsyncSession) -> None:
        incident = await create_incident(
            session,
            title="Test incident",
            raw_log="ERROR app timeout",
            severity=IncidentSeverity.HIGH,
        )
        fetched = await get_incident(session, incident.id)
        assert fetched is not None
        assert fetched.title == "Test incident"
        assert fetched.status == IncidentStatus.INVESTIGATING

    asyncio.run(_run_in_isolated_session(tmp_path, _logic))


def test_list_incidents(tmp_path: Path) -> None:
    async def _logic(session: AsyncSession) -> None:
        await create_incident(
            session, title="One", raw_log="error", severity=IncidentSeverity.LOW
        )
        await create_incident(
            session, title="Two", raw_log="error", severity=IncidentSeverity.LOW
        )
        incidents = await list_incidents(session, limit=10)
        assert len(incidents) == 2

    asyncio.run(_run_in_isolated_session(tmp_path, _logic))


def test_investigation_lifecycle(tmp_path: Path) -> None:
    async def _logic(session: AsyncSession) -> None:
        incident = await create_incident(
            session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM
        )
        investigation = await create_investigation(session, incident.id)
        completed = await mark_investigation_completed(
            session, investigation.id, confidence_score=0.85
        )
        assert completed.status == InvestigationStatus.COMPLETED
        assert completed.confidence_score == pytest.approx(0.85)

    asyncio.run(_run_in_isolated_session(tmp_path, _logic))


def test_resolve_incident(tmp_path: Path) -> None:
    async def _logic(session: AsyncSession) -> None:
        incident = await create_incident(
            session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM
        )
        resolved = await update_incident_status(
            session, incident.id, IncidentStatus.RESOLVED
        )
        assert resolved.status == IncidentStatus.RESOLVED

    asyncio.run(_run_in_isolated_session(tmp_path, _logic))


def test_create_report(tmp_path: Path) -> None:
    async def _logic(session: AsyncSession) -> None:
        incident = await create_incident(
            session, title="T", raw_log="err", severity=IncidentSeverity.MEDIUM
        )
        investigation = await create_investigation(session, incident.id)
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
        await create_or_update_report(session, report_data)
        fetched = await get_report_for_investigation(session, investigation.id)
        assert fetched is not None
        assert fetched.title == "Report"

    asyncio.run(_run_in_isolated_session(tmp_path, _logic))
