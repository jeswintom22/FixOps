from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

from fixops.db import KnowledgeCategory
from fixops.knowledge.loader import KnowledgeChunk


@dataclass
class ScoredChunk:
    chunk: KnowledgeChunk
    score: float


def tokenize(text: str) -> list[str]:
    return re.findall(r"[a-z0-9_]+", text.lower())


def compute_idf(chunks: Sequence[KnowledgeChunk]) -> dict[str, float]:
    """Compute inverse document frequency over the corpus of chunks."""
    doc_count = len(chunks)
    if doc_count == 0:
        return {}

    token_doc_freq: Counter[str] = Counter()
    for chunk in chunks:
        text = " ".join([chunk.content, *chunk.keywords])
        unique_tokens = set(tokenize(text))
        for token in unique_tokens:
            token_doc_freq[token] += 1

    idf: dict[str, float] = {}
    for token, df in token_doc_freq.items():
        idf[token] = math.log((doc_count + 1) / (df + 1)) + 1
    return idf


def score_chunks(query: str, chunks: Sequence[KnowledgeChunk], top_k: int = 5) -> list[ScoredChunk]:
    """Return the top-k chunks for a query using TF-IDF-style keyword scoring."""
    if not chunks:
        return []

    idf = compute_idf(chunks)
    query_tokens = Counter(tokenize(query))

    results: list[ScoredChunk] = []
    for chunk in chunks:
        text = " ".join([chunk.content, *chunk.keywords, chunk.source_file])
        chunk_tokens = Counter(tokenize(text))

        score = 0.0
        for token, q_count in query_tokens.items():
            if token in chunk_tokens:
                score += q_count * chunk_tokens[token] * idf.get(token, 1.0)

        # Small boost for runbooks/playbooks over postmortems for actionable content.
        if chunk.category in {KnowledgeCategory.RUNBOOK, KnowledgeCategory.PLAYBOOK}:
            score *= 1.05

        if score > 0:
            results.append(ScoredChunk(chunk=chunk, score=score))

    results.sort(key=lambda item: item.score, reverse=True)
    return results[:top_k]


class KeywordRetriever:
    """Simple in-memory retriever that uses the query text and keywords."""

    def __init__(self, chunks: Sequence[KnowledgeChunk]):
        self.chunks = list(chunks)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        category_filter: Sequence[KnowledgeCategory] | None = None,
        embedding: list[float] | None = None,
    ) -> list[KnowledgeChunk]:
        del embedding  # embeddings are not used by this retriever
        candidates = self.chunks
        if category_filter:
            categories = set(category_filter)
            candidates = [chunk for chunk in candidates if chunk.category in categories]
        scored = score_chunks(query, candidates, top_k=top_k)
        return [item.chunk for item in scored]
