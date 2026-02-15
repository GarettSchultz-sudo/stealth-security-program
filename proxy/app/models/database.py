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

# Build engine kwargs based on database type
engine_kwargs = {
    "echo": settings.is_development,
}
if not is_sqlite:
    engine_kwargs["pool_pre_ping"] = True
    engine_kwargs["pool_size"] = 10
    engine_kwargs["max_overflow"] = 20

engine = create_async_engine(settings.database_url, **engine_kwargs)

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
    # Skip table creation for SQLite - models use PostgreSQL-specific types like JSONB
    # In production, tables are created via Alembic migrations
    if is_sqlite:
        return

    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from app.models.base import Base  # noqa: F401

        # Tables will be created via Alembic migrations in production
        # For development/testing with PostgreSQL, we can create them directly
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
