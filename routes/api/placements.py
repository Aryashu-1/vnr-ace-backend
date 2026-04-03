from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.db import get_db
from models.student import Student
from models.placement import Placement

router = APIRouter(prefix="/placements", tags=["Placements API"])

@router.get("/")
async def get_placements(db: AsyncSession = Depends(get_db)):
    # Simple query for all placements
    result = (await db.execute(select(Placement))).scalars().all()
    return result

@router.get("/stats")
async def get_placement_stats(db: AsyncSession = Depends(get_db)):
    # total_students
    total_students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    
    # placed_students 
    # Use distinct student_ids in placements in case of multiple offers if represented
    placed_students = (await db.execute(select(func.count(func.distinct(Placement.student_id))))).scalar() or 0
    
    # placement_percentage
    placement_percentage = (placed_students / total_students * 100) if total_students > 0 else 0
    
    # highest_salary
    highest_salary = (await db.execute(select(func.max(Placement.ctc_lpa)))).scalar() or 0
    
    # average_salary
    average_salary = (await db.execute(select(func.avg(Placement.ctc_lpa)))).scalar() or 0
    
    # unplaced_students
    unplaced_students = total_students - placed_students

    return {
        "total_students": total_students,
        "placed_students": placed_students,
        "placement_percentage": round(placement_percentage, 2),
        "highest_salary": highest_salary,
        "average_salary": round(average_salary, 2),
        "unplaced_students": unplaced_students
    }
