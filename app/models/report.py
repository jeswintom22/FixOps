from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, UniqueConstraint, Uuid, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, UUIDPrimaryKeyMixin


class Report(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "reports"
    __table_args__ = (
        UniqueConstraint("investigation_id", name="idx_reports_investigation"),
        Index("idx_reports_incident", "incident_id"),
    )

    investigation_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text, nullable=False)
    incident_summary: Mapped[str] = mapped_column(Text, nullable=False)
    root_cause_section: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_section: Mapped[str] = mapped_column(Text, nullable=False)
    remediation_section: Mapped[str] = mapped_column(Text, nullable=False)
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    format_version: Mapped[str] = mapped_column(
        String(10),
        default="1.0",
        server_default="1.0",
        nullable=False,
    )

    investigation: Mapped["Investigation"] = relationship(back_populates="report")
    incident: Mapped["Incident"] = relationship(back_populates="reports")
