
import asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
import os
import sys

# Add the project root to sys.path
sys.path.append(os.getcwd())

from models.student import Student
from models.profile import Profile

DATABASE_URL = "postgresql+asyncpg://postgres.chevhdkfqfcupjdmkbud:k5kBfYAthCJeg@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres"

engine = create_async_engine(DATABASE_URL)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def check_students():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Student, Profile.email)
            .join(Profile, Profile.id == Student.profile_id)
        )
        rows = result.all()
        print("Students in DB:")
        if not rows:
            print("No students found.")
        for student, email in rows:
            print(f"- {email} (ID: {student.id}, Name: {student.full_name})")

if __name__ == "__main__":
    asyncio.run(check_students())
