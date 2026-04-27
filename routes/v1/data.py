from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from schemas.data import StudentResponse, CompanyResponse
from models.student import Student
from models.company import Company
from models.department import Department

router = APIRouter(prefix="/data", tags=["Data"])

@router.get("/students", response_model=List[StudentResponse])
async def get_students(
    branch: Optional[str] = None,
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Student)
    if branch:
        query = query.join(Department, Student.department_id == Department.id).where(Department.name == branch)
    query = query.limit(limit)
    result = await db.execute(query)
    students = result.scalars().all()
    
    # Ensure IDs are strings and branch is populated from department
    # Note: We might need to adjust StudentResponse schema if it expects 'branch' as a direct field
    return students

@router.get("/companies", response_model=List[CompanyResponse])
async def get_companies(
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    query = select(Company).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()
