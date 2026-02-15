"""Database connection and session management."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import get_settings

settings = get_settings()

# Create async engine (SQLite doesn't support pooling)
is_sqlite = "sqlite" in settings.database_url
engine = create_async_engine(
    settings.database_url,
    echo=settings.is_development,
    pool_pre_ping=not is_sqlite,
    pool_size=10 if not is_sqlite else None,
    max_overflow=20 if not is_sqlite else None,
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db() -> None:
    """Initialize database connection and create tables if needed."""
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.base import Base  # noqa: F401

        # Tables will be created via Alembic migrations in production
        # For development/testing, we can create them directly
        if settings.is_development:
            await conn.run_sync(Base.metadata.create_all)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides a database session."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
