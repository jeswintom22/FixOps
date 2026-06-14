from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TypeVar

from app.core.constants import IncidentSeverity
from app.services.azure_ai_service import AzureAIService

SchemaT = TypeVar("SchemaT")


@dataclass(slots=True)
class MockAzureAIService(AzureAIService):
    embedding_size: int = 16

    async def chat_complete(
        self,
        system_prompt: str,
        user_prompt: str,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        del system_prompt, response_format
        return (
            "MockAzureAIService generated a deterministic response. "
            f"Prompt excerpt: {user_prompt[:160]}"
        )

    async def embed(self, text: str) -> list[float]:
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
            return schema(**self._build_root_cause(prompt))
        if schema_name == "RemediationResponse":
            return schema(**self._build_remediation(prompt))
        if schema_name == "ReportResponse":
            return schema(**self._build_report(prompt))
        raise NotImplementedError(f"MockAzureAIService does not support schema {schema_name}.")

    def _build_log_analysis(self, prompt: str) -> dict[str, Any]:
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

    def _build_root_cause(self, prompt: str) -> dict[str, Any]:
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
    def _extract_timestamps(raw_log: str) -> tuple[datetime | None, datetime | None]:
        values = re.findall(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", raw_log)
        parsed = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in values]
        if not parsed:
            return (None, None)
        return (parsed[0], parsed[-1])
