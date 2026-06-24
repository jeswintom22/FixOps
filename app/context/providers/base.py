from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any
from uuid import UUID

from app.context.schemas.incident_context import ProviderContext, TimeWindow
from app.context.types.provider_types import AgentRole, ProviderCapability


class ContextProvider(ABC):
    provider_name: str
    supported_roles: set[AgentRole]
    capabilities: set[ProviderCapability]

    def __init__(
        self,
        provider_name: str,
        supported_roles: set[AgentRole],
        capabilities: set[ProviderCapability],
    ) -> None:
        self.provider_name = provider_name
        self.supported_roles = supported_roles
        self.capabilities = capabilities

    def supports_role(self, role: AgentRole) -> bool:
        return role in self.supported_roles

    def supports_capability(self, capability: ProviderCapability) -> bool:
        return capability in self.capabilities

    @abstractmethod
    async def fetch_context(
        self,
        incident_id: UUID,
        trace_id: str,
        time_window: TimeWindow | None = None,
        options: dict[str, Any] | None = None,
    ) -> ProviderContext:
        raise NotImplementedError
