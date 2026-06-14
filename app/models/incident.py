from typing import Any

from sqlalchemy import Enum, Index, String, Text, desc, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import DeploymentEnvironment, IncidentSeverity, IncidentStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Incident(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("idx_incidents_status", "status"),
        Index("idx_incidents_severity", "severity"),
        Index("idx_incidents_created", desc("created_at")),
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    raw_log: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, native_enum=False, length=20),
        default=IncidentSeverity.MEDIUM,
        server_default=IncidentSeverity.MEDIUM.value,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, length=30),
        default=IncidentStatus.OPEN,
        server_default=IncidentStatus.OPEN.value,
        nullable=False,
    )
    source: Mapped[str | None] = mapped_column(String(100))
    service_name: Mapped[str | None] = mapped_column(String(100))
    environment: Mapped[DeploymentEnvironment | None] = mapped_column(
        Enum(DeploymentEnvironment, native_enum=False, length=50)
    )
    tags: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        default=dict,
        server_default=text("'{}'::jsonb"),
        nullable=False,
    )

    investigations: Mapped[list["Investigation"]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
    )
    reports: Mapped[list["Report"]] = relationship(back_populates="incident")
