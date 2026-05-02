from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import Optional
from core.db import get_db
from models.student import Student
from models.profile import Profile
from models.department import Department
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2

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
        query = query.join(Profile, Student.profile_id == Profile.id).filter(
            (Profile.full_name.ilike(search_filter)) | 
            (Student.roll_no.ilike(search_filter))
        )

    if branch:
        query = query.join(Department, Student.department_id == Department.id).filter(
            func.upper(Department.name) == branch.upper()
        )
    
    if placed is not None or salary_min is not None:
        query = query.join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id, isouter=True)
        query = query.join(PlacementDrive, PlacementDrive.id == PlacementOfferV2.drive_id, isouter=True)
        
        if placed is True:
            query = query.filter(PlacementOfferV2.id.is_not(None))
        elif placed is False:
            query = query.filter(PlacementOfferV2.id.is_(None))
            
        if salary_min is not None:
            query = query.filter(PlacementOfferV2.offered_ctc >= salary_min)

    result = (await db.execute(query)).scalars().all()
    return result

@router.get("/{student_id}")
async def get_student(student_id: str, db: AsyncSession = Depends(get_db)):
    student = (await db.execute(select(Student).filter(Student.id == student_id))).scalar()
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    return student
