
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import uuid
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from models.student import Student
from models.profile import Profile

DATABASE_URL = "postgresql+asyncpg://postgres.chevhdkfqfcupjdmkbud:k5kBfYAthCJeg@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL, connect_args={"statement_cache_size": 0})
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def seed_student_for_admin():
    admin_email = "admin@vnr.com"
    async with AsyncSessionLocal() as session:
        # Get admin profile
        result = await session.execute(select(Profile).where(Profile.email == admin_email))
        profile = result.scalars().first()
        
        if not profile:
            print(f"Profile for {admin_email} not found.")
            return

        # Check if student already exists
        result = await session.execute(select(Student).where(Student.profile_id == profile.id))
        student = result.scalars().first()
        
        if student:
            print(f"Student record already exists for {admin_email} (ID: {student.id})")
        else:
            # Create student record
            new_student = Student(
                id=uuid.uuid4(),
                profile_id=profile.id,
                roll_no="ADMIN-001",
                current_year=4,
                cgpa=8.5,
                placement_status="not_placed"
            )
            session.add(new_student)
            await session.commit()
            print(f"Created student record for {admin_email} (ID: {new_student.id})")

if __name__ == "__main__":
    asyncio.run(seed_student_for_admin())
