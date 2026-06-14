from __future__ import annotations

import re
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from uuid import UUID

from sqlalchemy import bindparam, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import KnowledgeCategory
from app.models.knowledge_chunk import KnowledgeChunk
from app.services.ai import EmbeddingService
from app.services.knowledge_service import KnowledgeSearchResult, KnowledgeService

ProgressCallback = Callable[[Path, int], Awaitable[None] | None]


@dataclass(slots=True)
class DBKnowledgeService(KnowledgeService):
    session: AsyncSession
    embedding_service: EmbeddingService
    progress_callback: ProgressCallback | None = None

    async def ingest_documents(self, directory: Path) -> int:
        if not directory.exists():
            return 0

        total_chunks = 0
        for file_path in sorted(directory.rglob("*.md")):
            chunk_count = await self._ingest_file(directory=directory, file_path=file_path)
            total_chunks += chunk_count
            await self._emit_progress(file_path=file_path, chunk_count=chunk_count)

        return total_chunks

    async def search(
        self,
        query: str,
        top_k: int,
        category_filter: list[KnowledgeCategory] | None = None,
        embedding: list[float] | None = None,
    ) -> list[KnowledgeSearchResult]:
        del query
        if embedding is None:
            return []

        statement = text(
            """
            SELECT
                id,
                source_file,
                chunk_index,
                category,
                content,
                keywords,
                1 - (embedding <=> CAST(:query_embedding AS vector)) AS relevance_score
            FROM knowledge_chunks
            WHERE embedding IS NOT NULL
            """
        )
        parameters: dict[str, Any] = {
            "query_embedding": self._to_vector_literal(embedding),
            "top_k": top_k,
        }

        if category_filter:
            statement = text(
                f"""
                {statement.text}
                AND category IN :category_filter
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            ).bindparams(bindparam("category_filter", expanding=True))
            parameters["category_filter"] = [category.value for category in category_filter]
        else:
            statement = text(
                f"""
                {statement.text}
                ORDER BY embedding <=> CAST(:query_embedding AS vector)
                LIMIT :top_k
                """
            )

        result = await self.session.execute(statement, parameters)
        rows = result.mappings().all()
        return [self._map_row(row) for row in rows]

    async def get_chunk_by_id(self, chunk_id: UUID) -> KnowledgeSearchResult | None:
        chunk = await self.session.get(KnowledgeChunk, chunk_id)
        if chunk is None:
            return None
        return self._to_search_result(chunk)

    async def _ingest_file(self, *, directory: Path, file_path: Path) -> int:
        content = file_path.read_text(encoding="utf-8")
        paragraphs = [paragraph.strip() for paragraph in content.split("\n\n") if paragraph.strip()]
        if not paragraphs:
            return 0

        category = self._infer_category(file_path)
        source_file = str(file_path.relative_to(directory)).replace("\\", "/")
        chunk_count = 0

        try:
            for index, paragraph in enumerate(paragraphs):
                embedding = await self.embedding_service.embed(paragraph)
                statement = insert(KnowledgeChunk).values(
                    source_file=source_file,
                    chunk_index=index,
                    category=category,
                    content=paragraph,
                    keywords=self._extract_keywords(paragraph),
                    embedding=embedding,
                )
                statement = statement.on_conflict_do_update(
                    index_elements=["source_file", "chunk_index"],
                    set_={
                        "category": category,
                        "content": paragraph,
                        "keywords": self._extract_keywords(paragraph),
                        "embedding": embedding,
                    },
                )
                await self.session.execute(statement)
                chunk_count += 1

            await self.session.commit()
            return chunk_count
        except Exception:
            await self.session.rollback()
            raise

    async def _emit_progress(self, *, file_path: Path, chunk_count: int) -> None:
        if self.progress_callback is None:
            return
        maybe_awaitable = self.progress_callback(file_path, chunk_count)
        if maybe_awaitable is not None:
            await maybe_awaitable

    @staticmethod
    def _infer_category(file_path: Path) -> KnowledgeCategory | None:
        lowered = "/".join(part.lower() for part in file_path.parts)
        if "runbook" in lowered:
            return KnowledgeCategory.RUNBOOK
        if "playbook" in lowered:
            return KnowledgeCategory.PLAYBOOK
        if "postmortem" in lowered:
            return KnowledgeCategory.POSTMORTEM
        return None

    @staticmethod
    def _extract_keywords(content: str) -> list[str]:
        tokens = re.findall(r"[a-z0-9_]{4,}", content.lower())
        unique_tokens: list[str] = []
        for token in tokens:
            if token in unique_tokens:
                continue
            unique_tokens.append(token)
            if len(unique_tokens) == 12:
                break
        return unique_tokens

    @staticmethod
    def _to_vector_literal(embedding: list[float]) -> str:
        return "[" + ",".join(f"{value:.12f}" for value in embedding) + "]"

    @staticmethod
    def _map_row(row: Any) -> KnowledgeSearchResult:
        category = row["category"]
        return KnowledgeSearchResult(
            id=row["id"],
            source_file=row["source_file"],
            chunk_index=row["chunk_index"],
            category=KnowledgeCategory(category) if category is not None else None,
            content=row["content"],
            keywords=list(row["keywords"] or []),
            relevance_score=float(row["relevance_score"]) if row["relevance_score"] is not None else None,
        )

    @staticmethod
    def _to_search_result(chunk: KnowledgeChunk) -> KnowledgeSearchResult:
        return KnowledgeSearchResult(
            id=chunk.id,
            source_file=chunk.source_file,
            chunk_index=chunk.chunk_index,
            category=chunk.category,
            content=chunk.content,
            keywords=list(chunk.keywords),
            relevance_score=None,
        )
