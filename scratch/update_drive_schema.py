import asyncio
from sqlalchemy import text
from core.db import engine

async def update_schema():
    async with engine.begin() as conn:
        print("Updating placement_drives schema...")
        await conn.execute(text("""
            ALTER TABLE placement_drives 
            ADD COLUMN IF NOT EXISTS deadline DATE,
            ADD COLUMN IF NOT EXISTS criteria JSONB,
            ADD COLUMN IF NOT EXISTS external_registration_url TEXT,
            ADD COLUMN IF NOT EXISTS requires_external_registration BOOLEAN DEFAULT FALSE
        """))
    print("Schema updated successfully (Commit complete)")

if __name__ == "__main__":
    asyncio.run(update_schema())
