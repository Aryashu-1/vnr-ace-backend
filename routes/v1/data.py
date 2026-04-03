import json
from pathlib import Path
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.db import get_db
from schemas.data import StudentResponse, CompanyResponse
from models.student import Student
from models.company import Company

router = APIRouter(prefix="/data", tags=["Data"])

DATA_DIR = Path("data")
STUDENTS_FILE = DATA_DIR / "students_sample.json"
COMPANIES_FILE = DATA_DIR / "companies_sample.json"

def load_local_data(file_path: Path):
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)

@router.get("/students", response_model=List[StudentResponse])
async def get_students(
    branch: Optional[str] = None,
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Student)
        if branch:
            query = query.where(Student.branch == branch)
        query = query.limit(limit)
        
        result = await db.execute(query)
        students = result.scalars().all()
        if not students:
            raise Exception("No students in DB")
        return students
    except Exception:
        students = load_local_data(STUDENTS_FILE)
        if branch:
            students = [s for s in students if s.get("branch") == branch]
        return students[:limit]

@router.get("/companies", response_model=List[CompanyResponse])
async def get_companies(
    limit: int = Query(10, le=100),
    db: AsyncSession = Depends(get_db)
):
    try:
        query = select(Company).limit(limit)
        result = await db.execute(query)
        companies = result.scalars().all()
        if not companies:
            raise Exception("No companies in DB")
        return companies
    except Exception:
        companies = load_local_data(COMPANIES_FILE)
        return companies[:limit]
