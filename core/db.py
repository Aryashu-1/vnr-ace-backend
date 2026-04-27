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
# Fallback to a local SQLite database for development if env var is not set
if not DATABASE_URL:
    DATABASE_URL = "sqlite+aiosqlite:///./dev.db"
elif DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Async engine for PostgreSQL or SQLite
engine = create_async_engine(
    DATABASE_URL,
    echo=True,
    poolclass=NullPool if DATABASE_URL.startswith("postgresql") else None,
    connect_args={
        "ssl": "require" if DATABASE_URL.startswith("postgresql") else None,
        "command_timeout": 60,
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "prepared_statement_name_func": lambda: f"__asyncpg_{uuid4().hex}__",
    } if DATABASE_URL.startswith("postgresql") else {}
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
