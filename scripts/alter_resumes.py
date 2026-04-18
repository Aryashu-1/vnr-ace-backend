import asyncio
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import async_sessionmaker, engine
from sqlalchemy import text

async def alter_schema():
    async with engine.begin() as conn:
        print("Altering resumes table...")
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS user_id UUID REFERENCES profiles(id) ON DELETE CASCADE;"))
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS current_version_id BIGINT;"))
        await conn.execute(text("ALTER TABLE resumes ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now();"))
        print("Successfully updated resumes schema.")

if __name__ == "__main__":
    asyncio.run(alter_schema())
