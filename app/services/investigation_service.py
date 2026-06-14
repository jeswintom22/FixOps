from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import InvestigationStatus
from app.models.investigation import Investigation


@dataclass(slots=True)
class InvestigationService:
    session: AsyncSession

    async def create(self, investigation_data: dict[str, Any]) -> Investigation:
        try:
            investigation = Investigation(**investigation_data)
            self.session.add(investigation)
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(investigation)
            return investigation
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, investigation_id: UUID) -> Investigation | None:
        return await self.session.get(Investigation, investigation_id)

    async def get_active_by_incident_id(self, incident_id: UUID) -> Investigation | None:
        statement = (
            select(Investigation)
            .where(Investigation.incident_id == incident_id)
            .where(Investigation.status.in_([InvestigationStatus.QUEUED, InvestigationStatus.RUNNING]))
            .order_by(Investigation.created_at.desc())
        )
        result = await self.session.execute(statement)
        return result.scalars().first()

    async def mark_running(self, investigation_id: UUID) -> Investigation:
        return await self._update_status(
            investigation_id=investigation_id,
            status=InvestigationStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )

    async def mark_step_started(self, investigation_id: UUID, step_name: str) -> Investigation:
        investigation = await self._require(investigation_id)
        try:
            investigation.current_step = step_name
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(investigation)
            return investigation
        except Exception:
            await self.session.rollback()
            raise

    async def record_step_completion(
        self,
        investigation_id: UUID,
        step_name: str,
        step_order: int,
        output: dict[str, Any],
    ) -> Investigation:
        investigation = await self._require(investigation_id)
        del step_order, output
        try:
            investigation.current_step = step_name
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(investigation)
            return investigation
        except Exception:
            await self.session.rollback()
            raise

    async def mark_completed(self, investigation_id: UUID) -> Investigation:
        return await self._update_status(
            investigation_id=investigation_id,
            status=InvestigationStatus.COMPLETED,
            completed_at=datetime.now(timezone.utc),
            clear_error=True,
        )

    async def mark_failed(self, investigation_id: UUID, error: str) -> Investigation:
        investigation = await self._update_status(
            investigation_id=investigation_id,
            status=InvestigationStatus.FAILED,
            completed_at=datetime.now(timezone.utc),
        )
        try:
            investigation.current_step = None
            investigation.error_message = error
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(investigation)
            return investigation
        except Exception:
            await self.session.rollback()
            raise

    async def _update_status(
        self,
        *,
        investigation_id: UUID,
        status: InvestigationStatus,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
        clear_error: bool = False,
    ) -> Investigation:
        investigation = await self._require(investigation_id)
        try:
            investigation.status = status
            if started_at is not None and investigation.started_at is None:
                investigation.started_at = started_at
            if completed_at is not None:
                investigation.completed_at = completed_at
            if clear_error:
                investigation.error_message = None
            if status in {InvestigationStatus.COMPLETED, InvestigationStatus.FAILED}:
                investigation.current_step = None
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(investigation)
            return investigation
        except Exception:
            await self.session.rollback()
            raise

    async def _require(self, investigation_id: UUID) -> Investigation:
        investigation = await self.get_by_id(investigation_id)
        if investigation is None:
            raise LookupError(f"Investigation {investigation_id} was not found.")
        return investigation
