from __future__ import annotations

import os
from logging.config import fileConfig

import sqlmodel  # noqa: F401
from alembic import context
from sqlalchemy import engine_from_config, pool
from sqlmodel import SQLModel

import shared_models.monster  # noqa: F401
import shared_models.spell  # noqa: F401

# Import models to ensure they are registered on SQLModel.metadata
# Keep imports minimal to avoid side effects
import shared_models.user  # noqa: F401

# this is the Alembic Config object, which provides access to the values
# within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)


def build_database_url() -> str:
    """Construct DB URL from environment variables inside the container."""
    db_user = os.environ["POSTGRES_USER"]
    db_password = os.environ["POSTGRES_PASSWORD"]
    db_name = os.environ["POSTGRES_DB"]
    db_host = os.environ["POSTGRES_HOST"]
    db_port = os.environ["POSTGRES_PORT"]
    return f"postgresql+psycopg://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}"


target_metadata = SQLModel.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = build_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Configure SQLAlchemy engine from URL built above
    configuration = config.get_section(config.config_ini_section) or {}
    configuration["sqlalchemy.url"] = build_database_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        future=True,
    )

    with connectable.connect() as connection:
        def include_object(obj, name, type_, reflected, compare_to):
            # Skip GIN indexes managed exclusively via migrations
            if type_ == "index":
                return False
            return True

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()


