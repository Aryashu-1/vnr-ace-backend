
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the project root to sys.path to import models
sys.path.append(os.getcwd())

from models.placement_drive import PlacementDrive

DATABASE_URL = "postgresql+asyncpg://postgres.chevhdkfqfcupjdmkbud:k5kBfYAthCJeg@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_id():
    target_id = "764ac80e-14a1-4a85-8917-0320bc44520d"
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(PlacementDrive).where(str(PlacementDrive.id) == target_id))
        drive = result.scalars().first()
        if drive:
            print(f"Found drive: {drive.id}, role: {drive.role}")
        else:
            print("Drive not found.")
            # List all drives to see what IDs we have
            all_drives = await session.execute(select(PlacementDrive))
            print("All IDs in DB:")
            for d in all_drives.scalars().all():
                print(f"- {d.id} ({d.role})")

if __name__ == "__main__":
    asyncio.run(check_id())
