"""
Alembic Environment Configuration for Async PostgreSQL (SQLAlchemy 2.0).

This module manages the execution of database migrations in both 'offline'
(SQL script generation) and 'online' (direct async execution) modes.
It ensures all application models are registered, prevents empty migration
file generation, and handles async engine lifecycles cleanly.
"""

import asyncio
from logging.config import fileConfig
from typing import Any

# Importing app.models ensures all entities register on Base.metadata
import app.models  # noqa: F401
from alembic import context
from alembic.environment import MigrationContext
from alembic.operations.ops import MigrationScript

# ---------------------------------------------------------------------------
# 1. Application Configuration & Model Registration
# ---------------------------------------------------------------------------
# Import centralized application settings (12-Factor App config)
from app.core.config import settings
from app.models.base import Base
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

# Alembic Config object, providing access to values within alembic.ini
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for Alembic 'autogenerate' schema diffing
target_metadata = Base.metadata

# ---------------------------------------------------------------------------
# 2. Database Connection URL Resolution
# ---------------------------------------------------------------------------
# Sourced dynamically from app.core.config.settings.
# Percent signs are escaped (%%) to prevent configparser interpolation errors.
DATABASE_URL = str(settings.DATABASE_URL).replace("%", "%%")
config.set_main_option("sqlalchemy.url", DATABASE_URL)


# ---------------------------------------------------------------------------
# 3. Autogenerate Hooks & Optimizations
# ---------------------------------------------------------------------------
def process_revision_directives(
    context_obj: MigrationContext,
    revision: Any,
    directives: list[MigrationScript],
) -> None:
    """
    Prevents the creation of empty migration files when no schema changes occur.

    If 'alembic revision --autogenerate' detects zero changes between
    Base.metadata and PostgreSQL, it clears the directives list, preventing
    the generation of empty/duplicate revision files.
    """
    if config.cmd_opts and getattr(config.cmd_opts, "autogenerate", False):
        script = directives[0]
        if script.upgrade_ops and script.upgrade_ops.is_empty():
            directives[:] = []
            print("✨ No schema changes detected between models and database. Migration generation skipped.")


# ---------------------------------------------------------------------------
# 4. Offline Migration Execution
# ---------------------------------------------------------------------------
def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    Generates raw SQL statements without requiring an active database engine.
    Used for generating dry-run scripts for production deployment pipelines.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


# ---------------------------------------------------------------------------
# 5. Online Migration Execution (Async Engine)
# ---------------------------------------------------------------------------
def do_run_migrations(connection: Connection) -> None:
    """
    Executes migrations within a synchronous connection proxy.

    Configured with type comparison and server default comparison
    to ensure full fidelity between PostgreSQL and SQLAlchemy schemas.
    """
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        process_revision_directives=process_revision_directives,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Establishes an async connection using asyncpg and executes migrations.

    Uses NullPool because migration executions are short-lived CLI tasks
    and should not leave idle connections open in the connection pool.
    """
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migrations under an asyncio event loop."""
    asyncio.run(run_async_migrations())


# ---------------------------------------------------------------------------
# 6. Execution Mode Switcher
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
