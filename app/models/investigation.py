from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.constants import InvestigationStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Investigation(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "investigations"
    __table_args__ = (
        Index("idx_investigations_incident", "incident_id"),
        Index("idx_investigations_status", "status"),
    )

    incident_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, native_enum=False, length=30),
        default=InvestigationStatus.QUEUED,
        server_default=InvestigationStatus.QUEUED.value,
        nullable=False,
    )
    current_step: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    incident: Mapped["Incident"] = relationship(back_populates="investigations")
    report: Mapped["Report | None"] = relationship(
        back_populates="investigation",
        uselist=False,
        cascade="all, delete-orphan",
    )
