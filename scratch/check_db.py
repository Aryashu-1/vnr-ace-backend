
import asyncio
from sqlalchemy import select, func
from core.db import async_session
from models.student import Student
from models.profile import Profile

async def check():
    async with async_session() as db:
        students_count = await db.scalar(select(func.count(Student.id)))
        profiles_count = await db.scalar(select(func.count(Profile.id)))
        print(f"Students: {students_count}, Profiles: {profiles_count}")
        
        # Check first 5 students names
        result = await db.execute(select(Student).limit(5))
        students = result.scalars().all()
        for s in students:
            print(f"Roll: {s.roll_no}, Name: {s.full_name}")

if __name__ == "__main__":
    asyncio.run(check())
