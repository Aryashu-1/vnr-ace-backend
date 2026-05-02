import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from core.db import get_db
from core.deps import role_required
from models.interview_experience import InterviewExperience
from models.student import Student
from models.company import Company
from models.profile import Profile

router = APIRouter(prefix="/experiences", tags=["Admin Interview Experiences"])

class ExperienceCreateUpdate(BaseModel):
    student_id: Optional[uuid.UUID] = None
    company_id: uuid.UUID
    role: Optional[str] = None
    overall_experience: Optional[str] = None
    difficulty_level: Optional[str] = None
    tips: Optional[str] = None

@router.get("", response_model=List[dict])
async def list_experiences(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(InterviewExperience).options(
        joinedload(InterviewExperience.student).joinedload(Student.profile),
        joinedload(InterviewExperience.company)
    )
    result = await db.execute(query)
    exps = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "student_name": e.student.profile.full_name if e.student and e.student.profile else "Anonymous",
            "company": e.company.name if e.company else "Unknown",
            "role": e.role,
            "difficulty": e.difficulty_level,
            "date": e.created_at.strftime("%Y-%m-%d") if e.created_at else None,
            "content": e.overall_experience,
            "tips": e.tips
        } for e in exps
    ]

@router.post("")
async def create_or_update_experience(
    body: ExperienceCreateUpdate,
    exp_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if exp_id:
        exp = await db.get(InterviewExperience, exp_id)
        if not exp:
            raise HTTPException(status_code=404, detail="Experience not found")
        
        exp.student_id = body.student_id
        exp.company_id = body.company_id
        exp.role = body.role
        exp.overall_experience = body.overall_experience
        exp.difficulty_level = body.difficulty_level
        exp.tips = body.tips
    else:
        exp = InterviewExperience(
            id=uuid.uuid4(),
            student_id=body.student_id,
            company_id=body.company_id,
            role=body.role,
            overall_experience=body.overall_experience,
            difficulty_level=body.difficulty_level,
            tips=body.tips
        )
        db.add(exp)
    
    await db.commit()
    return {"status": "success", "id": str(exp.id)}

@router.delete("/{exp_id}")
async def delete_experience(
    exp_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    exp = await db.get(InterviewExperience, exp_id)
    if not exp:
        raise HTTPException(status_code=404, detail="Experience not found")
    
    await db.delete(exp)
    await db.commit()
    return {"status": "success"}
