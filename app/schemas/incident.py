from typing import Any

from pydantic import Field, field_serializer, field_validator

from app.core.constants import DeploymentEnvironment, IncidentSeverity, IncidentStatus
from app.schemas.common import AuditRead, ORMModel


class IncidentBase(ORMModel):
    title: str = Field(min_length=1, max_length=500)
    description: str | None = None
    raw_log: str = Field(min_length=1, max_length=20000)
    severity: IncidentSeverity = IncidentSeverity.MEDIUM
    status: IncidentStatus = IncidentStatus.OPEN
    source: str | None = Field(default=None, max_length=100)
    service_name: str | None = Field(default=None, max_length=100)
    environment: DeploymentEnvironment | None = None
    tags: list[str] = Field(default_factory=list, max_length=25)
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        alias="metadata_",
    )

    @field_validator("description")
    @classmethod
    def normalize_description(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        return normalized or None

    @field_validator("tags")
    @classmethod
    def normalize_tags(cls, value: list[str]) -> list[str]:
        normalized: list[str] = []
        for tag in value:
            candidate = tag.strip()
            if not candidate:
                continue
            if len(candidate) > 50:
                raise ValueError("Each tag must be 50 characters or fewer.")
            if candidate not in normalized:
                normalized.append(candidate)
        return normalized


class IncidentCreate(IncidentBase):
    pass


class IncidentUpdate(ORMModel):
    title: str | None = Field(default=None, max_length=500)
    description: str | None = None
    raw_log: str | None = Field(default=None, max_length=20000)
    severity: IncidentSeverity | None = None
    status: IncidentStatus | None = None
    source: str | None = Field(default=None, max_length=100)
    service_name: str | None = Field(default=None, max_length=100)
    environment: DeploymentEnvironment | None = None
    tags: list[str] | None = None
    metadata: dict[str, Any] | None = Field(
        default=None,
        alias="metadata_",
    )


class IncidentRead(IncidentBase, AuditRead):
    @field_serializer("metadata", when_used="json")
    def serialize_metadata(self, value: dict[str, Any] | None) -> dict[str, Any]:
        return value or {}
