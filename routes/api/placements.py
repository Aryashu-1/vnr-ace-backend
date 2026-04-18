from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.db import get_db
from models.student import Student
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.company import Company

router = APIRouter(prefix="/placements", tags=["Placements API"])

@router.get("/")
async def get_placements(db: AsyncSession = Depends(get_db)):
    query = (
        select(
            PlacementOfferV2.id,
            Student.roll_no,
            Student.full_name,
            Company.name.label("company"),
            PlacementOfferV2.offered_ctc,
            PlacementOfferV2.accepted,
            PlacementDrive.role,
            PlacementDrive.drive_date,
        )
        .join(Student, Student.id == PlacementOfferV2.student_id)
        .join(PlacementDrive, PlacementDrive.id == PlacementOfferV2.drive_id)
        .join(Company, Company.id == PlacementDrive.company_id)
    )
    rows = (await db.execute(query)).mappings().all()
    return [dict(row) for row in rows]

@router.get("/stats")
async def get_placement_stats(db: AsyncSession = Depends(get_db)):
    total_students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    placed_students = (
        await db.execute(select(func.count(func.distinct(PlacementOfferV2.student_id))))
    ).scalar() or 0
    placement_percentage = (placed_students / total_students * 100) if total_students > 0 else 0
    highest_salary = (await db.execute(select(func.max(PlacementOfferV2.offered_ctc)))).scalar() or 0
    average_salary = (await db.execute(select(func.avg(PlacementOfferV2.offered_ctc)))).scalar() or 0
    unplaced_students = total_students - placed_students
    return {
        "total_students": total_students,
        "placed_students": placed_students,
        "placement_percentage": round(placement_percentage, 2),
        "highest_salary": highest_salary,
        "average_salary": round(average_salary, 2),
        "unplaced_students": unplaced_students
    }
