from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from uuid import UUID

from app.core.constants import KnowledgeCategory


@dataclass(slots=True)
class KnowledgeSearchResult:
    id: UUID
    source_file: str
    chunk_index: int
    category: KnowledgeCategory | None
    content: str
    keywords: list[str] = field(default_factory=list)
    relevance_score: float | None = None


class KnowledgeService(ABC):
    @abstractmethod
    async def ingest_documents(self, directory: Path) -> int:
        raise NotImplementedError

    @abstractmethod
    async def search(
        self,
        query: str,
        top_k: int,
        category_filter: list[KnowledgeCategory] | None = None,
        embedding: list[float] | None = None,
    ) -> list[KnowledgeSearchResult]:
        raise NotImplementedError

    @abstractmethod
    async def get_chunk_by_id(self, chunk_id: UUID) -> KnowledgeSearchResult | None:
        raise NotImplementedError


@dataclass(slots=True)
class KnowledgeServiceStub(KnowledgeService):
    chunks: list[KnowledgeSearchResult] = field(default_factory=list)

    async def ingest_documents(self, directory: Path) -> int:
        return 0

    async def search(
        self,
        query: str,
        top_k: int,
        category_filter: list[KnowledgeCategory] | None = None,
        embedding: list[float] | None = None,
    ) -> list[KnowledgeSearchResult]:
        matches = [
            chunk
            for chunk in self.chunks
            if category_filter is None or chunk.category in category_filter
        ]
        matches.sort(key=lambda chunk: chunk.relevance_score or 0.0, reverse=True)
        return matches[:top_k]

    async def get_chunk_by_id(self, chunk_id: UUID) -> KnowledgeSearchResult | None:
        return next((chunk for chunk in self.chunks if chunk.id == chunk_id), None)
