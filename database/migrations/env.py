import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Import metadata
from core.config import settings


from core.db import Base
import models  # noqa: F401

# Access Alembic Config
config = context.config

# Interpret config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata for autogenerate
target_metadata = Base.metadata

def run_migrations_offline():
    """Offline mode."""
    context.configure(
        url=settings.DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection):
    """Sync migrations against connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online():
    """Online mode with sync engine."""
    import os
    from dotenv import load_dotenv
    load_dotenv()
    database_url = os.getenv("DATABASE_URL")
    
    if database_url and database_url.startswith("postgresql+asyncpg://"):
        database_url = database_url.replace("postgresql+asyncpg://", "postgresql+psycopg2://")
    
    configuration = config.get_section(config.config_ini_section)
    if database_url:
        configuration["sqlalchemy.url"] = database_url
        
    from sqlalchemy import engine_from_config
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
