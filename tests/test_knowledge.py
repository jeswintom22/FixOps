from pathlib import Path

import pytest

from fixops.db import KnowledgeCategory
from fixops.knowledge.loader import load_knowledge_base
from fixops.knowledge.retriever import KeywordRetriever, score_chunks


@pytest.fixture
def knowledge_dir(tmp_path: Path) -> Path:
    runbook_dir = tmp_path / "runbooks"
    runbook_dir.mkdir()
    (runbook_dir / "db_pool.md").write_text(
        "# DB Pool Runbook\n\n## Symptoms\nConnection timeouts.\n\n## Fix\nScale workers.",
        encoding="utf-8",
    )
    return tmp_path


def test_load_knowledge_base(knowledge_dir: Path) -> None:
    chunks = load_knowledge_base(knowledge_dir)
    assert len(chunks) == 2
    categories = {chunk.category for chunk in chunks}
    assert KnowledgeCategory.RUNBOOK in categories


def test_retriever_ranks_relevant_chunks(knowledge_dir: Path) -> None:
    import asyncio

    chunks = load_knowledge_base(knowledge_dir)
    retriever = KeywordRetriever(chunks)
    results = asyncio.run(retriever.search("connection timeout pool", top_k=2))
    assert len(results) >= 1
    assert any("db_pool.md" in chunk.source_file for chunk in results)


def test_score_chunks_empty() -> None:
    assert score_chunks("query", []) == []
