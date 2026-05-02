
import asyncio
from sqlalchemy.ext.asyncio import create_async_session_maker, AsyncSession
from sqlalchemy import select
from core.db import engine
from models.student import Student
from models.profile import Profile
from schemas.data import StudentResponse
from pydantic import TypeAdapter
from typing import List

async def test_serialization():
    async with engine.connect() as conn:
        async_session = create_async_session_maker(engine)
        async with async_session() as db:
            query = select(Student).options(
                joinedload := __import__('sqlalchemy.orm', fromlist=['joinedload']).joinedload,
                joinedload(Student.profile)
            ).limit(1)
            result = await db.execute(query)
            student = result.scalars().first()
            
            if not student:
                print("No student found in DB")
                return

            s_data = student.__dict__.copy()
            s_data.pop('_sa_instance_state', None)
            s_data['name'] = getattr(student.profile, 'full_name', "No Name")
            s_data['rollNumber'] = student.roll_no
            s_data['placed'] = student.placement_status == "placed"
            
            print(f"Manual s_data: {s_data}")
            
            response = StudentResponse.model_validate(s_data)
            print(f"Validated response model: {response}")
            print(f"JSON output: {response.model_dump(by_alias=False)}")

if __name__ == "__main__":
    asyncio.run(test_serialization())
