from enum import StrEnum


class IncidentSeverity(StrEnum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class IncidentStatus(StrEnum):
    OPEN = "OPEN"
    INVESTIGATING = "INVESTIGATING"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class InvestigationStatus(StrEnum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DeploymentEnvironment(StrEnum):
    PROD = "prod"
    STAGING = "staging"
    DEV = "dev"


class KnowledgeCategory(StrEnum):
    RUNBOOK = "RUNBOOK"
    PLAYBOOK = "PLAYBOOK"
    POSTMORTEM = "POSTMORTEM"
