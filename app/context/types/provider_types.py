from enum import Enum


class AgentRole(str, Enum):
    LOG = "LOG"
    METRIC = "METRIC"
    KNOWLEDGE = "KNOWLEDGE"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"
    COORDINATOR = "COORDINATOR"


class ContextProfile(str, Enum):
    INVESTIGATION = "INVESTIGATION"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"
    COORDINATION = "COORDINATION"
    FULL = "FULL"


class ContextSection(str, Enum):
    LOGS = "logs"
    METRICS = "metrics"
    MEMORY = "memory"
    VERIFICATION = "verification"


class ProviderCapability(str, Enum):
    LOGS = "LOGS"
    METRICS = "METRICS"
    MEMORY = "MEMORY"
    VERIFICATION = "VERIFICATION"
