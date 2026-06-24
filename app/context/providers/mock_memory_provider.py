from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.context.providers.base import ContextProvider
from app.context.schemas.incident_context import (
    MemoryContext,
    MemoryIncidentReference,
    KnowledgeEntryContext,
    RunbookContext,
    ProviderContext,
    ProviderProvenance,
    TimeWindow,
)
from app.context.types.provider_types import AgentRole, ContextSection, ProviderCapability


class MockMemoryProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="mock_memory_provider",
            supported_roles={AgentRole.KNOWLEDGE, AgentRole.COORDINATOR},
            capabilities={ProviderCapability.MEMORY},
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

        related_incidents = [
            MemoryIncidentReference(
                incident_id=UUID("00000000-0000-0000-0000-000000000001"),
                title="Database connection saturation",
                summary_snippet="Connections to database service reached the pool limit after a surge.",
                similarity_score=0.92,
                provenance=provenance,
            )
        ]

        knowledge_entries = [
            KnowledgeEntryContext(
                id=UUID("00000000-0000-0000-0000-000000000002"),
                type="SOLUTION",
                content="Increase DB connection pool size and add circuit breaker for retry storms.",
                confidence=0.88,
                similarity_score=0.95,
                provenance=provenance,
            )
        ]

        runbooks = [
            RunbookContext(
                id=UUID("00000000-0000-0000-0000-000000000003"),
                title="Database Connection Pool Exhaustion",
                excerpt="Verify current pool settings and adjust timeouts before scaling.",
                relevance_score=0.83,
                provenance=provenance,
            )
        ]

        payload = MemoryContext(
            related_incidents=related_incidents,
            knowledge_entries=knowledge_entries,
            applicable_runbooks=runbooks,
        )

        return ProviderContext(
            section_name=ContextSection.MEMORY,
            payload=payload.model_dump(),
            provenance=provenance,
            confidence=0.9,
        )
