from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, TypeVar

from ollama import AsyncClient as AsyncOllamaClient
from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import TypeAdapter

from app.config import Settings
from app.core.constants import IncidentSeverity

SchemaT = TypeVar("SchemaT")


class LLMService(ABC):
    @abstractmethod
    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        raise NotImplementedError

    @abstractmethod
    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        raise NotImplementedError


class EmbeddingService(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError


class ProviderAIService(LLMService, EmbeddingService, ABC):
    """Composite interface for providers that serve both chat and embeddings."""


@dataclass(slots=True)
class AIServiceStub(ProviderAIService):
    chat_handler: Callable[[str, str, dict[str, Any] | None], Awaitable[str]] | None = None
    embedding_handler: Callable[[str], Awaitable[list[float]]] | None = None
    structured_handler: Callable[[str, type[SchemaT]], Awaitable[SchemaT]] | None = None

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        if self.chat_handler is None:
            raise NotImplementedError("AIServiceStub.chat_complete has not been configured.")
        return await self.chat_handler(system_prompt, user_prompt, response_format)

    async def embed(self, text: str) -> list[float]:
        if self.embedding_handler is None:
            raise NotImplementedError("AIServiceStub.embed has not been configured.")
        return await self.embedding_handler(text)

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        if self.structured_handler is None:
            raise NotImplementedError("AIServiceStub.structured_complete has not been configured.")
        return await self.structured_handler(prompt, schema)


@dataclass(slots=True, frozen=True)
class AIProviderConfig:
    provider: str
    endpoint: str
    api_key: str
    api_version: str
    chat_model: str
    chat_deployment: str
    embedding_model: str
    embedding_deployment: str

    @classmethod
    def from_settings(cls, settings: Settings) -> "AIProviderConfig":
        return cls(
            provider=settings.resolved_ai_provider,
            endpoint=settings.endpoint,
            api_key=settings.api_key,
            api_version=settings.api_version,
            chat_model=settings.chat_model,
            chat_deployment=settings.chat_deployment,
            embedding_model=settings.embedding_model,
            embedding_deployment=settings.embedding_deployment,
        )

    @property
    def chat_target(self) -> str:
        return self.chat_deployment or self.chat_model

    @property
    def embedding_target(self) -> str:
        return self.embedding_deployment or self.embedding_model


@dataclass(slots=True)
class AzureOpenAIService(ProviderAIService):
    config: AIProviderConfig
    _client: AsyncAzureOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = AsyncAzureOpenAI(
            azure_endpoint=self.config.endpoint,
            api_key=self.config.api_key,
            api_version=self.config.api_version,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AzureOpenAIService":
        return cls(config=AIProviderConfig.from_settings(settings))

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self.config.chat_target,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        completion = await self._client.chat.completions.create(**request_kwargs)
        return completion.choices[0].message.content or ""

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        return await _structured_complete_with_openai_client(
            client=self._client,
            model=self.config.chat_target,
            prompt=prompt,
            schema=schema,
        )

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self.config.embedding_target,
            input=text,
        )
        return list(response.data[0].embedding)


@dataclass(slots=True)
class AzureFoundryService(ProviderAIService):
    config: AIProviderConfig
    _client: AsyncOpenAI = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self._client = AsyncOpenAI(
            base_url=self.config.endpoint,
            api_key=self.config.api_key,
            default_query={"api-version": self.config.api_version}
            if self.config.api_version
            else None,
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "AzureFoundryService":
        return cls(config=AIProviderConfig.from_settings(settings))

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        request_kwargs: dict[str, Any] = {
            "model": self.config.chat_target,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format is not None:
            request_kwargs["response_format"] = response_format

        completion = await self._client.chat.completions.create(**request_kwargs)
        return completion.choices[0].message.content or ""

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        return await _structured_complete_with_openai_client(
            client=self._client,
            model=self.config.chat_target,
            prompt=prompt,
            schema=schema,
        )

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self.config.embedding_target,
            input=text,
        )
        return list(response.data[0].embedding)


@dataclass(slots=True)
class OllamaService(ProviderAIService):
    config: AIProviderConfig
    _client: AsyncOllamaClient = field(init=False, repr=False)

    def __post_init__(self) -> None:
        kwargs: dict[str, Any] = {}
        if self.config.endpoint:
            kwargs["host"] = self.config.endpoint
        self._client = AsyncOllamaClient(**kwargs)

    @classmethod
    def from_settings(cls, settings: Settings) -> "OllamaService":
        return cls(config=AIProviderConfig.from_settings(settings))

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        del response_format
        response = await self._client.chat(
            model=self.config.chat_target,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        )
        return str(response.message.content or "")

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        schema_adapter = TypeAdapter(schema)
        response = await self._client.chat(
            model=self.config.chat_target,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Return only JSON that matches the provided schema. "
                        "Do not wrap the JSON in markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            format=schema_adapter.json_schema(),
        )
        content = str(response.message.content or "{}")
        return schema_adapter.validate_python(json.loads(content))

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embed(model=self.config.embedding_target, input=text)
        return [float(value) for value in response.embeddings[0]]


@dataclass(slots=True)
class MockAIService(ProviderAIService):
    embedding_size: int = 16

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        del system_prompt, response_format
        return (
            "MockAIService generated a deterministic response. "
            f"Prompt excerpt: {user_prompt[:160]}"
        )

    async def embed(self, text: str) -> list[float]:
        import hashlib

        digest = hashlib.sha256(text.encode("utf-8")).digest()
        values: list[float] = []
        for index in range(self.embedding_size):
            byte = digest[index % len(digest)]
            values.append(round((byte / 255.0) * 2 - 1, 6))
        return values

    async def structured_complete(self, prompt: str, schema: type[SchemaT]) -> SchemaT:
        schema_name = schema.__name__
        if schema_name == "LogSignalsResponse":
            return schema(**self._build_log_analysis(prompt))
        if schema_name == "RootCauseResponse":
            return schema(**self._build_root_cause())
        if schema_name == "RemediationResponse":
            return schema(**self._build_remediation(prompt))
        if schema_name == "ReportResponse":
            return schema(**self._build_report(prompt))
        raise NotImplementedError(f"MockAIService does not support schema {schema_name}.")

    def _build_log_analysis(self, prompt: str) -> dict[str, Any]:
        import re
        from datetime import datetime

        service_name = self._match(prompt, r"Service name:\s*(.+)")
        raw_log = self._extract_block(prompt, "Raw log:")
        timestamps = self._extract_timestamps(raw_log)
        lowered = raw_log.lower()

        if any(token in lowered for token in ("sqlstate 53300", "too many clients", "pool exhausted")):
            return {
                "error_type": "Database connection pool exhaustion",
                "affected_service": service_name,
                "key_terms": [
                    "SQLSTATE 53300",
                    "too many clients already",
                    "HikariPool connection timeout",
                    "payment authorization latency",
                ],
                "anomaly_signals": [
                    "Connection acquisition exceeded 30 seconds",
                    "Error rate spiked immediately after traffic increase",
                    "Readiness checks began failing while pods were still receiving traffic",
                ],
                "timestamp_start": timestamps[0],
                "timestamp_end": timestamps[1],
                "severity_assessment": IncidentSeverity.HIGH,
            }

        return {
            "error_type": "Application degradation",
            "affected_service": service_name,
            "key_terms": ["error spike", "latency increase"],
            "anomaly_signals": ["Repeated failures detected in raw logs"],
            "timestamp_start": timestamps[0],
            "timestamp_end": timestamps[1],
            "severity_assessment": IncidentSeverity.MEDIUM,
        }

    def _build_root_cause(self) -> dict[str, Any]:
        return {
            "primary_cause": (
                "The payments API exhausted its PostgreSQL connection pool during a traffic surge, "
                "which caused checkout requests to block until they timed out."
            ),
            "contributing_factors": [
                "Connection pool limits were lower than peak traffic demand.",
                "Stale connections were not reclaimed quickly after downstream slowness began.",
                "Pods continued receiving traffic while readiness checks were already degraded.",
            ],
            "confidence_score": 0.92,
            "reasoning_chain": (
                "The log pattern shows repeated Hikari pool timeouts and SQLSTATE 53300 errors. "
                "Matching runbooks describe the same symptom cluster as database connection exhaustion, "
                "and the postmortem context links readiness failures with overloaded payment workers."
            ),
            "evidence_refs": [
                {
                    "source_type": "log",
                    "source_ref": "incident_raw_log",
                    "content": "HikariPool connection acquisition exceeded 30000ms and SQLSTATE 53300 errors followed.",
                    "relevance_score": 0.98,
                },
                {
                    "source_type": "runbook",
                    "source_ref": "runbook_payments_db_pool.md#0",
                    "content": "Pool exhaustion guidance recommends validating active connections, reducing stuck workers, and scaling replicas.",
                    "relevance_score": 0.89,
                },
                {
                    "source_type": "postmortem",
                    "source_ref": "postmortem_checkout_peak_traffic.md#0",
                    "content": "A prior traffic surge produced the same timeout and readiness failure sequence.",
                    "relevance_score": 0.84,
                },
            ],
        }

    def _build_remediation(self, prompt: str) -> dict[str, Any]:
        automated = "No playbook context found." not in prompt
        return {
            "summary": (
                "Stabilize the service by relieving database pressure first, then restore normal capacity "
                "with safer pool settings and traffic controls."
            ),
            "steps": [
                {
                    "order": 1,
                    "action": "Temporarily scale out the payments API deployment to spread active requests across more workers.",
                    "rationale": "This reduces queueing pressure while the database recovers.",
                    "risk_level": "LOW",
                    "command_hint": "kubectl scale deployment payments-api --replicas=8 -n prod",
                    "is_automated": automated,
                },
                {
                    "order": 2,
                    "action": "Lower the application connection pool ceiling per pod and recycle unhealthy instances.",
                    "rationale": "A smaller per-pod pool prevents the cluster from overwhelming PostgreSQL.",
                    "risk_level": "MEDIUM",
                    "command_hint": "kubectl rollout restart deployment payments-api -n prod",
                    "is_automated": False,
                },
                {
                    "order": 3,
                    "action": "Inspect PostgreSQL active sessions and terminate long-idle blocked connections if they exceed the runbook threshold.",
                    "rationale": "This clears stuck capacity and confirms whether saturation is still ongoing.",
                    "risk_level": "MEDIUM",
                    "command_hint": "SELECT pid, state, query_start FROM pg_stat_activity WHERE datname = 'payments';",
                    "is_automated": False,
                },
                {
                    "order": 4,
                    "action": "Add a follow-up change to align autoscaling and connection-pool budgets before the next peak window.",
                    "rationale": "This addresses the structural cause instead of only restoring traffic.",
                    "risk_level": "LOW",
                    "command_hint": None,
                    "is_automated": False,
                },
            ],
        }

    def _build_report(self, prompt: str) -> dict[str, Any]:
        import re
        from datetime import UTC, datetime

        title = self._match(prompt, r"Incident title:\s*(.+)") or "Incident Investigation Report"
        timeline = [
            {
                "timestamp": "2026-06-11T09:14:00+00:00",
                "event": "Checkout latency began increasing as database connections approached saturation.",
            },
            {
                "timestamp": "2026-06-11T09:16:00+00:00",
                "event": "The payments API started emitting Hikari pool timeouts and SQLSTATE 53300 errors.",
            },
            {
                "timestamp": "2026-06-11T09:20:00+00:00",
                "event": "Readiness failures appeared on multiple pods, amplifying request retries and queueing.",
            },
            {
                "timestamp": "2026-06-11T09:27:00+00:00",
                "event": "Recommended stabilization actions focused on scaling out workers and constraining per-pod pool usage.",
            },
        ]
        del re
        return {
            "title": f"{title} - Investigation Report",
            "executive_summary": (
                "The incident was caused by database connection pool exhaustion in the payments API during a peak traffic window. "
                "The workflow correlated raw logs with runbook and postmortem evidence, then produced a staged remediation plan."
            ),
            "incident_summary": (
                "Customers experienced delayed or failed checkout attempts after the payments service began timing out while waiting "
                "for PostgreSQL connections. Symptoms intensified when degraded pods kept participating in traffic rotation."
            ),
            "root_cause_section": (
                "Primary cause: the payments API opened more concurrent database demand than the backend could safely serve. "
                "Contributing factors included aggressive pool sizing, slow recovery of unhealthy connections, and delayed traffic shedding."
            ),
            "evidence_section": (
                "Evidence included repeated SQLSTATE 53300 messages, Hikari acquisition timeouts, a matching runbook for connection "
                "pool exhaustion, and a prior peak-traffic postmortem with the same failure sequence."
            ),
            "remediation_section": (
                "The recommended response is to scale out the service, reduce per-pod pool pressure, inspect live PostgreSQL sessions, "
                "and schedule a follow-up change to align autoscaling policy with connection-budget limits."
            ),
            "timeline": timeline,
            "format_version": "1.0",
            "generated_at": datetime.now(UTC),
        }

    @staticmethod
    def _match(text: str, pattern: str) -> str | None:
        import re

        match = re.search(pattern, text)
        if match is None:
            return None
        return match.group(1).strip()

    @staticmethod
    def _extract_block(prompt: str, header: str) -> str:
        if header not in prompt:
            return prompt
        return prompt.split(header, maxsplit=1)[1].strip()

    @staticmethod
    def _extract_timestamps(raw_log: str) -> tuple[Any | None, Any | None]:
        import re
        from datetime import datetime

        values = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", raw_log)
        parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in values]
        if not parsed:
            return (None, None)
        return (parsed[0], parsed[-1])


async def _structured_complete_with_openai_client(
    *,
    client: AsyncAzureOpenAI | AsyncOpenAI,
    model: str,
    prompt: str,
    schema: type[SchemaT],
) -> SchemaT:
    schema_adapter = TypeAdapter(schema)
    schema_name = getattr(schema, "__name__", "StructuredResponse")
    json_schema = schema_adapter.json_schema()
    schema_payload = {
        "name": schema_name,
        "schema": json_schema,
        "strict": True,
    }
    completion = await client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": (
                    "Return only JSON that matches the provided schema. "
                    "Do not wrap the JSON in markdown."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": schema_payload,
        },
    )
    content = completion.choices[0].message.content or "{}"
    return schema_adapter.validate_python(json.loads(content))
