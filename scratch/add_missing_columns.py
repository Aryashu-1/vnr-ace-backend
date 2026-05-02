import asyncio
import os
from sqlalchemy import text
from core.db import engine

async def add_missing_columns():
    print("Starting database schema alignment...")
    
    commands = [
        # Profiles table
        "ALTER TABLE profiles ADD COLUMN IF NOT EXISTS hashed_password TEXT;",
        
        # Students table
        "ALTER TABLE students ADD COLUMN IF NOT EXISTS attendance DOUBLE PRECISION DEFAULT 0.0;",
        
        # Departments table
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS code TEXT UNIQUE;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS intake TEXT;",
        "ALTER TABLE departments ADD COLUMN IF NOT EXISTS hod TEXT;",
        
        # Placement Drives table
        "ALTER TABLE placement_drives ADD COLUMN IF NOT EXISTS deadline DATE;",
        "ALTER TABLE placement_drives ADD COLUMN IF NOT EXISTS criteria JSONB;",
        "ALTER TABLE placement_drives ADD COLUMN IF NOT EXISTS external_registration_url TEXT;",
        "ALTER TABLE placement_drives ADD COLUMN IF NOT EXISTS requires_external_registration BOOLEAN DEFAULT FALSE;",
    ]
    
    async with engine.begin() as conn:
        for cmd in commands:
            try:
                print(f"Executing: {cmd}")
                await conn.execute(text(cmd))
            except Exception as e:
                print(f"Error executing command: {e}")
                
    print("Database schema alignment completed.")

if __name__ == "__main__":
    asyncio.run(add_missing_columns())
