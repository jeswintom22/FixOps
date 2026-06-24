from __future__ import annotations

from datetime import datetime
from uuid import UUID

from app.context.providers.base import ContextProvider
from app.context.schemas.incident_context import (
    MetricContext,
    MetricEntry,
    SLOViolation,
    ProviderContext,
    ProviderProvenance,
    TimeWindow,
)
from app.context.types.provider_types import AgentRole, ContextSection, ProviderCapability


class MockMetricProvider(ContextProvider):
    def __init__(self) -> None:
        super().__init__(
            provider_name="mock_metric_provider",
            supported_roles={AgentRole.METRIC, AgentRole.COORDINATOR},
            capabilities={ProviderCapability.METRICS},
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

        metrics = [
            MetricEntry(
                name="cpu_usage",
                baseline=32.0,
                current=87.5,
                delta_pct=173.4,
                trend="rising",
                provenance=provenance,
            ),
            MetricEntry(
                name="request_latency_ms",
                baseline=120.0,
                current=580.0,
                delta_pct=383.3,
                trend="spike",
                provenance=provenance,
            ),
        ]

        violations = [
            SLOViolation(
                metric_name="error_rate",
                threshold="<1%",
                current_value=4.6,
                provenance=provenance,
            )
        ]

        payload = MetricContext(key_metrics=metrics, slo_violations=violations)

        return ProviderContext(
            section_name=ContextSection.METRICS,
            payload=payload.model_dump(),
            provenance=provenance,
            confidence=0.8,
        )
