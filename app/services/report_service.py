from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.report import Report


@dataclass(slots=True)
class ReportService:
    session: AsyncSession

    async def create(self, investigation_id: UUID, report_data: dict[str, Any]) -> Report:
        try:
            existing = await self.get_by_investigation(investigation_id)
            if existing is None:
                report = Report(**report_data)
                self.session.add(report)
            else:
                report = existing
                for key, value in report_data.items():
                    setattr(report, key, value)

            await self.session.flush()
            await self.session.commit()
            await self.session.refresh(report)
            return report
        except Exception:
            await self.session.rollback()
            raise

    async def get_by_id(self, report_id: UUID) -> Report | None:
        return await self.session.get(Report, report_id)

    async def get_by_investigation(self, investigation_id: UUID) -> Report | None:
        statement = select(Report).where(Report.investigation_id == investigation_id)
        result = await self.session.execute(statement)
        return result.scalar_one_or_none()
