"""
Alembic Environment Configuration
Async-compatible, reads DB URL from app settings, imports all models.
"""

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# ---------------------------------------------------------------------------
# Load application settings & models so Alembic sees them for autogenerate
# ---------------------------------------------------------------------------
from app.core.config import settings  # noqa: E402

# Import Base and ALL model modules so every table is registered on Base.metadata
from app.db.models import Base  # noqa: E402
import app.db.models  # noqa: E402, F401 – registers Client, Lead, Conversation, etc.
import app.db.models_auth  # noqa: E402, F401 – registers User, UserSession, AuditLog

# ---------------------------------------------------------------------------
# Alembic Config object (provides access to alembic.ini values)
# ---------------------------------------------------------------------------
config = context.config

# Wire the database URL from our application settings into Alembic's config
# so we never need to duplicate it in alembic.ini.
config.set_main_option(
    "sqlalchemy.url",
    settings.database_url.get_secret_value().replace("+asyncpg", ""),
)

# Set up Python loggers from the ini file
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# This is the MetaData that Alembic will diff against the database
target_metadata = Base.metadata


# ---------------------------------------------------------------------------
# Autogenerate filters — suppress known cosmetic diffs
# ---------------------------------------------------------------------------

# Indexes managed outside Alembic (e.g. IVFFlat pgvector indexes)
_EXTERNALLY_MANAGED_INDEXES = {
    "ix_knowledge_chunks_embedding",
}


def include_object(object, name, type_, reflected, compare_to):
    """Exclude externally-managed indexes from autogenerate."""
    if type_ == "index" and name in _EXTERNALLY_MANAGED_INDEXES:
        return False
    return True


def _is_uuid_default_noise(op):
    """
    Detect 'modify_default' on UUID PK columns where DB already has
    gen_random_uuid() — Alembic can't match the function representation.
    """
    if not isinstance(op, list):
        return False
    for sub in op:
        if isinstance(sub, tuple) and len(sub) >= 4:
            if sub[0] == "modify_default" and str(sub[3]).endswith("id"):
                # Check if existing type is UUID (PK default noise)
                info = sub[4] if len(sub) > 4 else {}
                from sqlalchemy.dialects.postgresql import UUID as PG_UUID
                if isinstance(info.get("existing_type"), PG_UUID):
                    return True
    return False


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — emits SQL to stdout, no DB connection.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Configure and run migrations with a live connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations in 'online' mode using an async engine.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        # Override back to asyncpg for the actual connection
        url=settings.database_url.get_secret_value(),
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations — delegates to async runner."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
