import asyncio
from sqlalchemy import text
from core.db import engine

async def update_schema():
    async with engine.begin() as conn:
        print("Updating placement_applications schema...")
        await conn.execute(text("""
            ALTER TABLE placement_applications 
            ADD COLUMN IF NOT EXISTS is_registered_externally BOOLEAN DEFAULT FALSE,
            ADD COLUMN IF NOT EXISTS external_registration_id TEXT,
            ADD COLUMN IF NOT EXISTS confirmation_screenshot_url TEXT
        """))
    print("Schema updated successfully (Commit complete)")

if __name__ == "__main__":
    asyncio.run(update_schema())
