from collections.abc import AsyncIterator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import get_settings
from app.models.base import Base

settings = get_settings()

engine = create_async_engine(
    settings.database_url,
    echo=settings.db_echo,
    pool_pre_ping=True,
    pool_recycle=1800,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    expire_on_commit=False,
)


async def get_db_session() -> AsyncIterator[AsyncSession]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


async def init_db() -> None:
    async with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            # pgvector is required for the knowledge chunk embedding column.
            await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        # Create all tables
        await connection.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    await engine.dispose()
