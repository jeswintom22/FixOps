from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from app.agent.state import AgentState, KnowledgeChunkContext
from app.agent.steps.base import AgentStep
from app.core.constants import KnowledgeCategory
from app.services.ai import EmbeddingService
from app.services.knowledge_service import KnowledgeService, KnowledgeSearchResult


@dataclass(slots=True)
class KnowledgeRetrievalStep(AgentStep):
    embedding_service: EmbeddingService
    knowledge_service: KnowledgeService
    name: str = "KNOWLEDGE_RETRIEVAL"
    order: int = 2

    async def execute(self, state: AgentState) -> AgentState:
        if state.log_signals is None:
            raise ValueError("Log analysis must complete before knowledge retrieval.")

        embedding = await self.embedding_service.embed(self._build_query(state))
        runbooks = await self.knowledge_service.search(
            query=self._build_query(state),
            top_k=5,
            category_filter=[KnowledgeCategory.RUNBOOK, KnowledgeCategory.PLAYBOOK],
            embedding=embedding,
        )
        postmortems = await self.knowledge_service.search(
            query=self._build_query(state),
            top_k=3,
            category_filter=[KnowledgeCategory.POSTMORTEM],
            embedding=embedding,
        )

        combined = runbooks + postmortems
        combined.sort(key=lambda chunk: chunk.relevance_score or 0.0, reverse=True)
        state.knowledge_chunks = [
            KnowledgeChunkContext(
                id=chunk.id,
                source_file=chunk.source_file,
                chunk_index=chunk.chunk_index,
                category=chunk.category,
                content=chunk.content,
                keywords=list(chunk.keywords),
                relevance_score=chunk.relevance_score,
            )
            for chunk in combined[:8]
        ]
        return state

    def build_output(self, state: AgentState) -> dict[str, Any]:
        return {
            "knowledge_chunks": [asdict(chunk) for chunk in state.knowledge_chunks],
        }

    def _build_query(self, state: AgentState) -> str:
        assert state.log_signals is not None
        parts = [
            state.log_signals.error_type,
            state.log_signals.affected_service or state.service_name or "",
            *state.log_signals.key_terms,
            *state.log_signals.anomaly_signals,
        ]
        return " | ".join(part for part in parts if part)
