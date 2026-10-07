from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
from typing import Any

from fixops.config import get_settings
from fixops.db import IncidentSeverity, KnowledgeCategory
from fixops.knowledge.retriever import KeywordRetriever
from fixops.pipeline.state import AgentState, KnowledgeChunkContext
from fixops.pipeline.steps.base import AgentStep


class KnowledgeRetrievalStep(AgentStep):
    name = "KNOWLEDGE_RETRIEVAL"
    order = 2

    def __init__(self, retriever: KeywordRetriever, top_k: int = 5) -> None:
        self.retriever = retriever
        self.top_k = top_k

    async def execute(
        self,
        state: AgentState,
        *,
        top_k: int | None = None,
        query_suffix: str | None = None,
    ) -> AgentState:
        if state.log_signals is None:
            raise ValueError("Log analysis must complete before knowledge retrieval")

        effective_top_k = top_k if top_k is not None else self.top_k
        query = self._build_query(state, query_suffix=query_suffix)

        runbooks = await self.retriever.search(
            query=query,
            top_k=effective_top_k,
            category_filter=[KnowledgeCategory.RUNBOOK, KnowledgeCategory.PLAYBOOK],
        )
        postmortem_top_k = max(1, min(3, effective_top_k))
        postmortems = await self.retriever.search(
            query=query,
            top_k=postmortem_top_k,
            category_filter=[KnowledgeCategory.POSTMORTEM],
        )

        combined = runbooks + postmortems
        # Re-score is implicit in the retriever; here we just merge and deduplicate.
        seen: set[str] = set()
        state.knowledge_chunks = []
        for chunk in combined:
            key = f"{chunk.source_file}#{chunk.chunk_index}"
            if key in seen:
                continue
            seen.add(key)
            state.knowledge_chunks.append(
                KnowledgeChunkContext(
                    source_file=chunk.source_file,
                    chunk_index=chunk.chunk_index,
                    category=chunk.category.value if chunk.category else None,
                    content=chunk.content,
                    keywords=list(chunk.keywords),
                    relevance_score=None,
                )
            )
            if len(state.knowledge_chunks) >= effective_top_k:
                break
        return state

    def build_output(self, state: AgentState) -> Mapping[str, Any]:
        return {
            "knowledge_chunks": [asdict(chunk) for chunk in state.knowledge_chunks],
        }

    def _build_query(self, state: AgentState, *, query_suffix: str | None = None) -> str:
        assert state.log_signals is not None
        parts = [
            state.log_signals.error_type,
            state.log_signals.affected_service or state.service_name or "",
            *state.log_signals.key_terms,
            *state.log_signals.anomaly_signals,
        ]
        if query_suffix:
            parts.append(query_suffix)
        return " | ".join(part for part in parts if part)


def select_top_k(severity: IncidentSeverity | None) -> int:
    settings = get_settings()
    if severity in {IncidentSeverity.CRITICAL, IncidentSeverity.HIGH}:
        return settings.top_k_high_severity
    return settings.top_k_default
