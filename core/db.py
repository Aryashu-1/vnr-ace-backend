import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# Base class for all models

load_dotenv()
Base = declarative_base()
DATABASE_URL = os.getenv("DATABASE_URL")
# Async engine for PostgreSQL
engine = create_async_engine(
    DATABASE_URL,  # Update with your database URL
    echo=True,  # shows SQL queries in terminal, helpful for debugging
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
