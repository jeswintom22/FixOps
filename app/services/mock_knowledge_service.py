from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID, uuid5

from app.core.constants import KnowledgeCategory
from app.services.knowledge_service import (
    KnowledgeSearchResult,
    KnowledgeService,
)


@dataclass(slots=True)
class MockKnowledgeService(KnowledgeService):
    chunks: list[KnowledgeSearchResult] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.chunks:
            return
        self.chunks = [
            self._chunk(
                source_file="runbook_payments_db_pool.md",
                chunk_index=0,
                category=KnowledgeCategory.RUNBOOK,
                keywords=["payments", "postgres", "connection pool", "sqlstate 53300", "timeouts"],
                relevance_score=0.94,
                content=(
                    "When payments-api logs SQLSTATE 53300 or repeated connection acquisition timeouts, "
                    "check active PostgreSQL sessions, confirm pool sizing per replica, and scale application "
                    "pods before increasing database limits."
                ),
            ),
            self._chunk(
                source_file="playbook_checkout_hotfix.md",
                chunk_index=0,
                category=KnowledgeCategory.PLAYBOOK,
                keywords=["checkout", "traffic surge", "kubernetes", "scale out", "restart"],
                relevance_score=0.91,
                content=(
                    "For checkout degradation under peak traffic, first scale the payments deployment, then roll "
                    "unhealthy pods after lowering per-pod connection limits. Avoid immediate database restarts."
                ),
            ),
            self._chunk(
                source_file="runbook_postgres_session_pressure.md",
                chunk_index=1,
                category=KnowledgeCategory.RUNBOOK,
                keywords=["postgres", "sessions", "idle in transaction", "pool saturation"],
                relevance_score=0.87,
                content=(
                    "If session pressure remains high, inspect pg_stat_activity for long-idle or blocked sessions "
                    "and terminate only the connections exceeding the runbook threshold."
                ),
            ),
            self._chunk(
                source_file="postmortem_checkout_peak_traffic.md",
                chunk_index=0,
                category=KnowledgeCategory.POSTMORTEM,
                keywords=["checkout", "peak traffic", "payments", "pool exhaustion", "readiness"],
                relevance_score=0.88,
                content=(
                    "A previous Black Friday incident showed that oversized application pools exhausted the shared "
                    "PostgreSQL tier, while degraded readiness probes caused retries that amplified saturation."
                ),
            ),
            self._chunk(
                source_file="postmortem_worker_retry_storm.md",
                chunk_index=2,
                category=KnowledgeCategory.POSTMORTEM,
                keywords=["retries", "backpressure", "latency", "overload"],
                relevance_score=0.73,
                content=(
                    "Retry amplification can hide the original bottleneck, so confirm the first failing shared "
                    "resource before tuning downstream timeouts."
                ),
            ),
        ]

    async def ingest_documents(self, directory: Path) -> int:
        del directory
        return len(self.chunks)

    async def search(
        self,
        query: str,
        top_k: int,
        category_filter: list[KnowledgeCategory] | None = None,
        embedding: list[float] | None = None,
    ) -> list[KnowledgeSearchResult]:
        del embedding
        query_tokens = set(self._tokenize(query))
        results: list[KnowledgeSearchResult] = []

        for chunk in self.chunks:
            if category_filter is not None and chunk.category not in category_filter:
                continue

            chunk_tokens = set(self._tokenize(" ".join([chunk.content, *chunk.keywords, chunk.source_file])))
            overlap = len(query_tokens & chunk_tokens)
            base_score = chunk.relevance_score or 0.0
            score = round(base_score + overlap * 0.02, 4)

            results.append(
                KnowledgeSearchResult(
                    id=chunk.id,
                    source_file=chunk.source_file,
                    chunk_index=chunk.chunk_index,
                    category=chunk.category,
                    content=chunk.content,
                    keywords=list(chunk.keywords),
                    relevance_score=score,
                )
            )

        results.sort(key=lambda item: item.relevance_score or 0.0, reverse=True)
        return results[:top_k]

    async def get_chunk_by_id(self, chunk_id: UUID) -> KnowledgeSearchResult | None:
        return next((chunk for chunk in self.chunks if chunk.id == chunk_id), None)

    @staticmethod
    def _chunk(
        *,
        source_file: str,
        chunk_index: int,
        category: KnowledgeCategory,
        keywords: list[str],
        relevance_score: float,
        content: str,
    ) -> KnowledgeSearchResult:
        return KnowledgeSearchResult(
            id=uuid5(UUID("11111111-1111-1111-1111-111111111111"), f"{source_file}:{chunk_index}"),
            source_file=source_file,
            chunk_index=chunk_index,
            category=category,
            content=content,
            keywords=keywords,
            relevance_score=relevance_score,
        )

    @staticmethod
    def _tokenize(value: str) -> list[str]:
        return re.findall(r"[a-z0-9_]+", value.lower())
