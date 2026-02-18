"""
Database Connection and Session Management
Async SQLAlchemy with connection pooling for PostgreSQL
"""
from sqlalchemy import text
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from app.core.config import settings

# Create async engine with connection pooling
engine: AsyncEngine = create_async_engine(
    settings.database_url.get_secret_value(),
    pool_size=settings.database_pool_size,
    max_overflow=settings.database_max_overflow,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug and settings.is_development,
)

# For testing or serverless environments, use NullPool
engine_no_pool: AsyncEngine = create_async_engine(
    settings.database_url.get_secret_value(),
    poolclass=NullPool,
    echo=settings.debug and settings.is_development,
)

# Session factory
async_session_factory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency for FastAPI routes to get database session.
    Automatically handles commit/rollback/close.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def get_db_context() -> AsyncGenerator[AsyncSession, None]:
    """
    Context manager for getting database session outside of FastAPI.
    Use in background tasks, scripts, etc.
    """
    async with async_session_factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database connection and verify connectivity.
    Called on application startup.
    """
    from app.db.models import Base

    async with engine.connect() as conn:
        # Create all tables (in production, use Alembic migrations instead)
        if settings.is_development:
            await conn.execute(text("SELECT 1"))


async def close_db() -> None:
    """
    Close database connections.
    Called on application shutdown.
    """
    await engine.dispose()


# =============================================================================
# Multi-tenant context management
# =============================================================================


class TenantContext:
    """
    Context for current tenant/client operations.
    Used to enforce row-level security in queries.
    """

    _current_client_id: str | None = None

    @classmethod
    def set_client_id(cls, client_id: str) -> None:
        cls._current_client_id = client_id

    @classmethod
    def get_client_id(cls) -> str | None:
        return cls._current_client_id

    @classmethod
    def clear(cls) -> None:
        cls._current_client_id = None


@asynccontextmanager
async def tenant_context(client_id: str) -> AsyncGenerator[None, None]:
    """
    Context manager to set tenant context for database operations.
    """
    TenantContext.set_client_id(client_id)
    try:
        yield
    finally:
        TenantContext.clear()

# Alias for backward compatibility
get_db = get_db_session
