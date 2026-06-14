from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Enum, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.constants import KnowledgeCategory
from app.models.base import Base, CreatedAtMixin, UUIDPrimaryKeyMixin


class KnowledgeChunk(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    __tablename__ = "knowledge_chunks"
    __table_args__ = (
        UniqueConstraint("source_file", "chunk_index", name="uq_knowledge_source_chunk"),
        Index(
            "idx_knowledge_embedding",
            "embedding",
            postgresql_using="ivfflat",
            postgresql_with={"lists": 100},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index("idx_knowledge_source", "source_file"),
        Index("idx_knowledge_category", "category"),
    )

    source_file: Mapped[str] = mapped_column(String(255), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    category: Mapped[KnowledgeCategory | None] = mapped_column(
        Enum(KnowledgeCategory, native_enum=False, length=50)
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    keywords: Mapped[list[str]] = mapped_column(
        JSONB,
        default=list,
        server_default=text("'[]'::jsonb"),
        nullable=False,
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1536))
