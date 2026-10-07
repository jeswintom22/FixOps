from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from fixops.db import KnowledgeCategory


@dataclass
class KnowledgeChunk:
    source_file: str
    chunk_index: int
    category: KnowledgeCategory | None
    content: str
    keywords: list[str] = field(default_factory=list)


CATEGORY_MAP = {
    "runbooks": KnowledgeCategory.RUNBOOK,
    "runbook": KnowledgeCategory.RUNBOOK,
    "playbooks": KnowledgeCategory.PLAYBOOK,
    "playbook": KnowledgeCategory.PLAYBOOK,
    "postmortems": KnowledgeCategory.POSTMORTEM,
    "postmortem": KnowledgeCategory.POSTMORTEM,
}


def infer_category(file_path: Path) -> KnowledgeCategory | None:
    lowered = "/".join(part.lower() for part in file_path.parts)
    for key, category in CATEGORY_MAP.items():
        if key in lowered:
            return category
    return None


def extract_keywords(content: str) -> list[str]:
    """Extract a small set of meaningful keywords from a chunk."""
    tokens = re.findall(r"[a-z0-9_]{4,}", content.lower())
    seen: set[str] = set()
    keywords: list[str] = []
    for token in tokens:
        if token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) == 16:
            break
    return keywords


def split_into_chunks(
    source_file: str, text: str, category: KnowledgeCategory | None
) -> list[KnowledgeChunk]:
    """Split a markdown file into chunks by top-level heading sections."""
    # Drop the title heading if it is the only top-level content.
    # Split on ## headings.
    heading_pattern = re.compile(r"^(?=##\s+)", re.MULTILINE)
    parts = heading_pattern.split(text)
    if not parts:
        return []

    chunks: list[KnowledgeChunk] = []
    preamble = parts[0].strip()
    # If preamble has meaningful content beyond the H1 title, include it.
    if preamble and len(preamble.split()) > 5:
        chunks.append(_make_chunk(source_file, 0, category, preamble))

    for index, part in enumerate(parts[1:], start=len(chunks)):
        part = part.strip()
        if not part:
            continue
        chunks.append(_make_chunk(source_file, index, category, part))

    # If no headings were found, treat the whole file as one chunk.
    if not chunks and text.strip():
        chunks.append(_make_chunk(source_file, 0, category, text.strip()))

    return chunks


def _make_chunk(
    source_file: str,
    chunk_index: int,
    category: KnowledgeCategory | None,
    content: str,
) -> KnowledgeChunk:
    return KnowledgeChunk(
        source_file=source_file,
        chunk_index=chunk_index,
        category=category,
        content=content,
        keywords=extract_keywords(content),
    )


def load_knowledge_base(directory: Path) -> list[KnowledgeChunk]:
    """Load all markdown files under directory as knowledge chunks."""
    chunks: list[KnowledgeChunk] = []
    if not directory.exists():
        return chunks
    for file_path in sorted(directory.rglob("*.md")):
        category = infer_category(file_path)
        source_file = str(file_path.relative_to(directory)).replace("\\", "/")
        text = file_path.read_text(encoding="utf-8")
        chunks.extend(split_into_chunks(source_file, text, category))
    return chunks
