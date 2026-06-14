from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import IncidentStatus
from app.models.incident import Incident


@dataclass(slots=True)
class IncidentService:
    session: AsyncSession

    async def create(self, incident_data: dict[str, Any]) -> Incident:
        payload = dict(incident_data)
        metadata = payload.pop("metadata", None)
        if metadata is not None:
            payload["metadata_"] = metadata

        try:
            incident = Incident(**payload)
            self.session.add(incident)
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(incident)
            return incident
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, incident_id: UUID) -> Incident | None:
        return await self.session.get(Incident, incident_id)

    async def update_status(self, incident_id: UUID, status: IncidentStatus) -> Incident:
        incident = await self.get_by_id(incident_id)
        if incident is None:
            raise LookupError(f"Incident {incident_id} was not found.")

        try:
            incident.status = status
            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(incident)
            return incident
        except Exception:
            await self.session.rollback()
            raise
