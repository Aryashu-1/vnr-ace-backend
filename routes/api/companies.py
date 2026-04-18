from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.db import get_db
from models.company import Company
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.student import Student

router = APIRouter(prefix="/companies", tags=["Companies API"])

@router.get("/")
async def get_companies(db: AsyncSession = Depends(get_db)):
    result = (await db.execute(select(Company))).scalars().all()
    return result

@router.get("/{company_id}")
async def get_company(company_id: str, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company).filter(Company.id == company_id))).scalar()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    return company

@router.get("/{company_id}/hired_students")
async def get_hired_students(company_id: str, db: AsyncSession = Depends(get_db)):
    query = (
        select(Student)
        .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
        .join(PlacementDrive, PlacementDrive.id == PlacementOfferV2.drive_id)
        .filter(PlacementDrive.company_id == company_id)
    )
    students = (await db.execute(query)).scalars().all()
    return students
