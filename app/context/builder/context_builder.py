from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from app.context.providers.base import ContextProvider
from app.context.schemas.incident_context import (
    IncidentContext,
    ProviderContext,
    ProviderProvenance,
    ProviderStatus,
    TimeWindow,
)
from app.context.types.provider_types import (
    AgentRole,
    ContextProfile,
    ContextSection,
    ProviderCapability,
)

CAPABILITY_TO_SECTION: dict[ProviderCapability, ContextSection] = {
    ProviderCapability.LOGS: ContextSection.LOGS,
    ProviderCapability.METRICS: ContextSection.METRICS,
    ProviderCapability.MEMORY: ContextSection.MEMORY,
    ProviderCapability.VERIFICATION: ContextSection.VERIFICATION,
}


class ContextBuilder:
    def __init__(self, providers: list[ContextProvider]) -> None:
        self.providers = providers

    async def build_context(
        self,
        incident_id: UUID,
        trace_id: str,
        role: AgentRole,
        profile: ContextProfile = ContextProfile.FULL,
        time_window: TimeWindow | None = None,
        options: dict[str, Any] | None = None,
    ) -> IncidentContext:
        provider_contexts: list[ProviderContext] = []
        diagnostics: list[ProviderStatus] = []

        profile_capabilities: dict[ContextProfile, set[ProviderCapability]] = {
            ContextProfile.INVESTIGATION: {ProviderCapability.LOGS, ProviderCapability.METRICS, ProviderCapability.MEMORY},
            ContextProfile.REMEDIATION: {ProviderCapability.MEMORY},
            ContextProfile.VERIFICATION: {ProviderCapability.VERIFICATION, ProviderCapability.METRICS},
            ContextProfile.COORDINATION: {ProviderCapability.LOGS, ProviderCapability.METRICS, ProviderCapability.MEMORY, ProviderCapability.VERIFICATION},
            ContextProfile.FULL: {ProviderCapability.LOGS, ProviderCapability.METRICS, ProviderCapability.MEMORY, ProviderCapability.VERIFICATION},
        }

        requested_capabilities = profile_capabilities.get(profile, set())

        for provider in self.providers:
            if not any(provider.supports_capability(cap) for cap in requested_capabilities):
                continue

            try:
                context = await provider.fetch_context(
                    incident_id=incident_id,
                    trace_id=trace_id,
                    time_window=time_window,
                    options=options,
                )
                provider_contexts.append(context)
                diagnostics.append(
                    ProviderStatus(
                        provider_name=provider.provider_name,
                        section=context.section_name,
                        status="SUCCESS",
                        message="",
                        trace_id=trace_id,
                    )
                )
            except Exception as exc:
                failure_section = next(
                    (CAPABILITY_TO_SECTION[cap] for cap in provider.capabilities),
                    ContextSection.LOGS,
                )
                diagnostics.append(
                    ProviderStatus(
                        provider_name=provider.provider_name,
                        section=failure_section,
                        status="FAILURE",
                        message=str(exc),
                        trace_id=trace_id,
                    )
                )
                continue

        context = IncidentContext(
            incident_id=incident_id,
            trace_id=trace_id,
            generated_at=datetime.utcnow(),
            summary="Incident context assembled",
            severity=IncidentSeverity.MEDIUM,
            service_name=None,
            environment=None,
            time_window=time_window,
            providers_used=[ctx.provenance.provider_name for ctx in provider_contexts],
            provenance=[ctx.provenance for ctx in provider_contexts],
            provider_diagnostics=diagnostics,
            logs=None,
            metrics=None,
            memory=None,
        )

        for provider_context in provider_contexts:
            section = provider_context.section_name
            if section == ContextSection.LOGS:
                context.logs = provider_context.payload if isinstance(provider_context.payload, dict) else provider_context.payload
            elif section == ContextSection.METRICS:
                context.metrics = provider_context.payload if isinstance(provider_context.payload, dict) else provider_context.payload
            elif section == ContextSection.MEMORY:
                context.memory = provider_context.payload if isinstance(provider_context.payload, dict) else provider_context.payload
            elif section == ContextSection.VERIFICATION:
                context.verification = provider_context.payload if isinstance(provider_context.payload, dict) else provider_context.payload

        return context
