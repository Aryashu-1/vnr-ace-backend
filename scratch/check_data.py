
import asyncio
from sqlalchemy import select, func
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

async def check():
    async with AsyncSessionLocal() as session:
        # Check for NULL roles
        count_null = await session.scalar(select(func.count()).select_from(PlacementDrive).where(PlacementDrive.role == None))
        print(f"Drives with NULL role: {count_null}")
        
        if count_null > 0:
            print("Cleaning up...")
            from sqlalchemy import delete
            await session.execute(delete(PlacementDrive).where(PlacementDrive.role == None))
            await session.commit()
            print("Cleanup done.")
        
        # Check total count
        total = await session.scalar(select(func.count()).select_from(PlacementDrive))
        print(f"Total drives: {total}")

if __name__ == "__main__":
    asyncio.run(check())
