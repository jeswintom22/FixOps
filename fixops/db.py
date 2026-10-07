from __future__ import annotations

import enum
import json
import logging
import uuid
from collections.abc import AsyncIterator
from datetime import datetime
from typing import Any, cast

from sqlalchemy import JSON, DateTime, Enum, ForeignKey, Index, String, Text, Uuid, func
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from fixops.config import get_settings

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class StrEnum(str, enum.Enum):
    def __str__(self) -> str:
        return cast(str, self.value)


class IncidentSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    ANALYZED = "ANALYZED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class InvestigationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class KnowledgeCategory(StrEnum):
    RUNBOOK = "RUNBOOK"
    PLAYBOOK = "PLAYBOOK"
    POSTMORTEM = "POSTMORTEM"


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    raw_log: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, native_enum=False, length=20),
        default=IncidentSeverity.MEDIUM,
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, length=30),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    source: Mapped[str | None] = mapped_column(String(100))
    service_name: Mapped[str | None] = mapped_column(String(100))
    environment: Mapped[str | None] = mapped_column(String(50))
    tags: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata", JSON, default=dict, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    investigations: Mapped[list[Investigation]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    reports: Mapped[list[Report]] = relationship(
        back_populates="incident",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Investigation(Base):
    __tablename__ = "investigations"
    __table_args__ = (
        Index("idx_investigations_incident_id", "incident_id"),
        Index("idx_investigations_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    status: Mapped[InvestigationStatus] = mapped_column(
        Enum(InvestigationStatus, native_enum=False, length=30),
        default=InvestigationStatus.QUEUED,
        nullable=False,
    )
    current_step: Mapped[str | None] = mapped_column(String(50))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    root_cause_retried: Mapped[bool] = mapped_column(default=False, nullable=False)
    remediation_retried: Mapped[bool] = mapped_column(default=False, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    incident: Mapped[Incident] = relationship(back_populates="investigations")
    report: Mapped[Report | None] = relationship(
        back_populates="investigation",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Report(Base):
    __tablename__ = "reports"
    __table_args__ = (
        Index("idx_reports_investigation_id", "investigation_id"),
        Index("idx_reports_incident_id", "incident_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    investigation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("investigations.id", ondelete="CASCADE"),
        nullable=False,
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
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
    timeline: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list, nullable=False)
    remediation_steps: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )
    root_cause_retried: Mapped[bool] = mapped_column(default=False, nullable=False)
    remediation_retried: Mapped[bool] = mapped_column(default=False, nullable=False)
    confidence_score: Mapped[float | None] = mapped_column()
    format_version: Mapped[str] = mapped_column(String(10), default="1.0", nullable=False)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    investigation: Mapped[Investigation] = relationship(back_populates="report")
    incident: Mapped[Incident] = relationship(back_populates="reports")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        Index("idx_knowledge_source", "source_file"),
        Index("idx_knowledge_category", "category"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_index: Mapped[int] = mapped_column(nullable=False)
    category: Mapped[KnowledgeCategory | None] = mapped_column(
        Enum(KnowledgeCategory, native_enum=False, length=50)
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    embedding: Mapped[list[float] | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )


class _DateTimeEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> Any:
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


def _sqlite_json_serializer(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, cls=_DateTimeEncoder)


def make_engine(database_path: str) -> Any:
    return create_async_engine(
        f"sqlite+aiosqlite:///{database_path}",
        json_serializer=_sqlite_json_serializer,
        echo=False,
        pool_pre_ping=True,
    )


async def init_db() -> None:
    settings = get_settings()
    engine = make_engine(str(settings.database_path))
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
    logger.info("Database initialized at %s", settings.database_path)


async def get_session() -> AsyncIterator[AsyncSession]:
    settings = get_settings()
    engine = make_engine(str(settings.database_path))
    session_factory = async_sessionmaker(
        bind=engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autoflush=False,
    )
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
            await engine.dispose()
