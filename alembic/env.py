# alembic/env.py
from __future__ import annotations

import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# --- logging from alembic.ini ---
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- make project importable (add repo root to sys.path) ---
ROOT = Path(__file__).resolve().parents[1]  # repo root (parent of /alembic)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# --- load env vars from .env (optional but convenient) ---
try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv(ROOT / ".env")
except Exception:
    pass  # safe to ignore if python-dotenv isn't installed

# --- import your metadata for autogenerate ---
# Note: Import must be after path setup, so E402 is expected here
# Import all models to ensure they're registered with Base.metadata
from src import models  # noqa: E402, F401
from src.core.database import Base  # noqa: E402

# --- point Alembic at your DB URL (prefer env var over alembic.ini) ---
database_url = os.getenv("DATABASE_URL")
if database_url:
    config.set_main_option("sqlalchemy.url", database_url)

target_metadata = Base.metadata


# --- offline migrations ---
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


# --- online migrations ---
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
