import os
from uuid import uuid4
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool

# Base class for all models

load_dotenv()
Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL")
if DATABASE_URL and DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Async engine for PostgreSQL using NullPool since Supabase has PgBouncer
engine = create_async_engine(
    DATABASE_URL,  # Update with your database URL
    echo=True,  # shows SQL queries in terminal, helpful for debugging
    poolclass=NullPool,
    connect_args={
        "ssl": "require",
        "command_timeout": 60,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    }
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    expire_on_commit=False,
)   

# Dependency for FastAPI routes
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
