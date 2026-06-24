from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.context.providers.base import ContextProvider
from app.context.schemas.incident_context import (
    ProviderContext,
    ProviderProvenance,
    TimeWindow,
    VerificationContext,
)
from app.context.types.provider_types import AgentRole, ContextSection, ProviderCapability


class MockVerificationProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="mock_verification_provider",
            supported_roles={AgentRole.VERIFICATION, AgentRole.COORDINATOR},
            capabilities={ProviderCapability.VERIFICATION},
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

        payload = VerificationContext(
            verification_status="PENDING",
            evidence_summary=[
                "Action execution in progress",
                "Verification threshold not yet met",
            ],
        )

        return ProviderContext(
            section_name=ContextSection.VERIFICATION,
            payload=payload,
            provenance=provenance,
            confidence=0.7,
        )
