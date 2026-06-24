from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.context.providers.base import ContextProvider
from app.context.schemas.incident_context import (
    LogContext,
    LogSnippet,
    ProviderContext,
    ProviderProvenance,
    TimeWindow,
)
from app.context.types.provider_types import AgentRole, ContextSection, ProviderCapability


class MockLogProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="mock_log_provider",
            supported_roles={AgentRole.LOG, AgentRole.COORDINATOR},
            capabilities={ProviderCapability.LOGS},
        )

    async def fetch_context(
        self,
        incident_id: UUID,
        trace_id: str,
        time_window: TimeWindow | None = None,
        options: dict[str, object] | None = None,
    ) -> ProviderContext:
        provenance = ProviderProvenance(
            provider_name=self.provider_name,
            trace_id=trace_id,
            timestamp=datetime.utcnow(),
            source="mock",
        )

        snippets = [
            LogSnippet(
                snippet="ERROR 503: upstream connection failed for service inventory",
                timestamp=datetime.utcnow(),
                source="app-logs",
                severity_tag="ERROR",
                provenance=provenance,
            ),
            LogSnippet(
                snippet="WARN: retry loop exceeded threshold after 3 attempts",
                timestamp=datetime.utcnow(),
                source="app-logs",
                severity_tag="WARN",
                provenance=provenance,
            ),
        ]

        payload = LogContext(top_snippets=snippets, error_count=1, trace_links=["trace-1234", "trace-5678"])

        return ProviderContext(
            section_name=ContextSection.LOGS,
            payload=payload.model_dump(),
            provenance=provenance,
            confidence=0.75,
        )
