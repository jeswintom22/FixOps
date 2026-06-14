from pydantic import Field

from app.core.constants import KnowledgeCategory
from app.schemas.common import TimestampedRead, ORMModel


class KnowledgeChunkBase(ORMModel):
    source_file: str
    chunk_index: int
    category: KnowledgeCategory | None = None
    content: str
    keywords: list[str] = Field(default_factory=list)
    embedding: list[float] | None = None


class KnowledgeChunkCreate(KnowledgeChunkBase):
    pass


class KnowledgeChunkRead(KnowledgeChunkBase, TimestampedRead):
    pass
