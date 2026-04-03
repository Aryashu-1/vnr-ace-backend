from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from typing import Optional
from core.db import get_db
from models.student import Student
from models.placement import Placement
from models.offer import Offer

router = APIRouter(prefix="/students", tags=["Students API"])

@router.get("/")
async def get_students(
    search: Optional[str] = None,
    branch: Optional[str] = None,
    placed: Optional[bool] = None,
    salary_min: Optional[float] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(Student)
    
    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Student.full_name.ilike(search_filter)) | 
            (Student.roll_no.ilike(search_filter))
        )

    if branch:
        query = query.filter(Student.branch == branch.upper())
    
    # Needs a join if checking placements 
    if placed is not None or salary_min is not None:
        query = query.join(Placement, Placement.student_id == Student.id, isouter=True)
        
        if placed is True:
            # Placed if there is a placement record
            query = query.filter(Placement.id != None)
        elif placed is False:
            query = query.filter(Placement.id == None)
            
        if salary_min is not None:
            query = query.filter(Placement.ctc_lpa >= salary_min)

    result = (await db.execute(query)).scalars().all()
    return result

@router.get("/{student_id}")
async def get_student(student_id: int, db: AsyncSession = Depends(get_db)):
    student = (await db.execute(select(Student).filter(Student.id == student_id))).scalar()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
