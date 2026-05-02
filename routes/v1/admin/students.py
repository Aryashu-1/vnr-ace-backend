import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, delete, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.db import get_db
from core.deps import role_required
from models.student import Student
from models.profile import Profile

router = APIRouter(prefix="/students", tags=["Admin Students"])

class StudentCreateUpdate(BaseModel):
    roll_no: str
    full_name: str
    section: Optional[str] = None
    current_year: Optional[int] = None
    attendance: Optional[float] = None # Percentage

@router.get("", response_model=List[dict])
async def list_students_admin(
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(Student).options(joinedload(Student.profile))
    
    if search:
        search_filter = or_(
            Student.roll_no.ilike(f"%{search}%"),
            Profile.full_name.ilike(f"%{search}%")
        )
        query = query.join(Profile).filter(search_filter)
    
    result = await db.execute(query.order_by(Student.roll_no))
    students = result.scalars().all()
    
    return [
        {
            "id": str(s.id),
            "rollNo": s.roll_no,
            "name": s.profile.full_name if s.profile else "N/A",
            "section": s.section,
            "year": s.current_year,
            "attendance": f"{s.attendance}%"
        } for s in students
    ]

@router.post("")
async def create_or_update_student(
    body: StudentCreateUpdate,
    student_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if student_id:
        student = await db.get(Student, student_id)
        if not student:
            raise HTTPException(status_code=404, detail="Student not found")
        
        student.roll_no = body.roll_no
        student.section = body.section
        student.current_year = body.current_year
        student.attendance = body.attendance
        
        if student.profile:
            student.profile.full_name = body.full_name
    else:
        # For a new student, we might need a profile too
        profile = Profile(
            id=uuid.uuid4(),
            full_name=body.full_name
        )
        db.add(profile)
        
        student = Student(
            id=uuid.uuid4(),
            roll_no=body.roll_no,
            profile_id=profile.id,
            section=body.section,
            current_year=body.current_year,
            attendance=body.attendance
        )
        db.add(student)
    
    await db.commit()
    return {"status": "success"}

@router.delete("/{student_id}")
async def delete_student(
    student_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    student = await db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")
    
    await db.delete(student)
    await db.commit()
    return {"status": "success"}
