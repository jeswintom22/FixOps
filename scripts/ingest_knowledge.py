from __future__ import annotations

import asyncio
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.config import get_settings
from app.db.session import AsyncSessionLocal
from app.services.ai_factory import get_embedding_service
from app.services.db_knowledge_service import DBKnowledgeService


async def main() -> None:
    settings = get_settings()
    knowledge_base_dir = REPO_ROOT / "knowledge_base"

    async def report_progress(file_path: Path, chunk_count: int) -> None:
        print(f"Ingested {chunk_count} chunks from {file_path.relative_to(REPO_ROOT)}")

    async with AsyncSessionLocal() as session:
        service = DBKnowledgeService(
            session=session,
            embedding_service=get_embedding_service(),
            progress_callback=report_progress,
        )
        total = await service.ingest_documents(knowledge_base_dir)

    print(f"Knowledge ingestion complete with provider {settings.resolved_ai_provider}.")
    print(f"Total chunks ingested: {total}")


if __name__ == "__main__":
    asyncio.run(main())
