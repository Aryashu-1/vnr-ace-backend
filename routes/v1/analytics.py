from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, extract

from core.db import get_db
from schemas.analytics import ChartDataPoint, PlacementTrendResponse, BranchWiseResponse, SalaryDistributionResponse, TopHiringResponse, MinorImpactResponse, MultipleOffersResponse
from models.student import Student
from models.company import Company
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.department import Department

router = APIRouter(prefix="/analytics", tags=["Analytics"])

@router.get("/placement-trend", response_model=PlacementTrendResponse)
async def get_placement_trend(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(extract('year', PlacementDrive.drive_date).label('year'), func.count(PlacementOfferV2.id))
        .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
        .where(PlacementDrive.drive_date.is_not(None))
        .group_by('year')
        .order_by('year')
    )
    data = [ChartDataPoint(name=str(int(year)), value=count) for year, count in result.all() if year is not None]
    return PlacementTrendResponse(data=data)

@router.get("/branch-wise", response_model=BranchWiseResponse)
async def get_branch_wise_stats(db: AsyncSession = Depends(get_db)):
    totals = (await db.execute(
        select(Department.name, func.count(Student.id))
        .join(Student, Student.department_id == Department.id)
        .group_by(Department.name)
    )).all()
    
    placed = (
        await db.execute(
            select(Department.name, func.count(func.distinct(Student.id)))
            .join(Student, Student.department_id == Department.id)
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .group_by(Department.name)
        )
    ).all()
    placed_map = {branch: count for branch, count in placed}
    data = []
    for branch, total in totals:
        placed_count = placed_map.get(branch, 0)
        percentage = round((placed_count / total * 100), 1) if total > 0 else 0
        data.append(ChartDataPoint(name=branch or "Other", value=placed_count, total=total, percentage=percentage))
    return BranchWiseResponse(data=data)

@router.get("/salary-distribution", response_model=SalaryDistributionResponse)
async def get_salary_distribution(db: AsyncSession = Depends(get_db)):
    rows = (await db.execute(select(PlacementOfferV2.offered_ctc))).scalars().all()
    buckets = {"0-5 LPA": 0, "5-10 LPA": 0, "10-15 LPA": 0, "15+ LPA": 0}
    for ctc in rows:
        ctc = ctc or 0
        if ctc < 5: buckets["0-5 LPA"] += 1
        elif ctc < 10: buckets["5-10 LPA"] += 1
        elif ctc < 15: buckets["10-15 LPA"] += 1
        else: buckets["15+ LPA"] += 1
    data = [ChartDataPoint(name=k, value=v) for k, v in buckets.items()]
    return SalaryDistributionResponse(data=data)

@router.get("/top-hiring", response_model=TopHiringResponse)
async def get_top_hiring(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Company.name, func.count(PlacementOfferV2.id))
        .join(PlacementDrive, PlacementDrive.company_id == Company.id)
        .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
        .group_by(Company.name)
        .order_by(func.count(PlacementOfferV2.id).desc())
        .limit(10)
    )
    data = [ChartDataPoint(name=name, value=count) for name, count in result.all()]
    return TopHiringResponse(data=data)

@router.get("/minor-impact", response_model=MinorImpactResponse)
async def get_minor_impact(db: AsyncSession = Depends(get_db)):
    with_minor = (await db.execute(select(func.count(Student.id)).where(Student.minor_degree.is_not(None)))).scalar() or 0
    without_minor = (await db.execute(select(func.count(Student.id)).where(Student.minor_degree.is_(None)))).scalar() or 0
    placed_with = (
        await db.execute(
            select(func.count(func.distinct(Student.id)))
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .where(Student.minor_degree.is_not(None))
        )
    ).scalar() or 0
    placed_without = (
        await db.execute(
            select(func.count(func.distinct(Student.id)))
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .where(Student.minor_degree.is_(None))
        )
    ).scalar() or 0
    data = [
        ChartDataPoint(name="With Minor", value=placed_with, total=with_minor),
        ChartDataPoint(name="Without Minor", value=placed_without, total=without_minor)
    ]
    return MinorImpactResponse(data=data)

@router.get("/multiple-offers", response_model=MultipleOffersResponse)
async def get_multiple_offers(db: AsyncSession = Depends(get_db)):
    students = (await db.execute(select(Student.id))).scalars().all()
    counts = dict(
        (await db.execute(select(PlacementOfferV2.student_id, func.count(PlacementOfferV2.id)).group_by(PlacementOfferV2.student_id))).all()
    )
    distribution = {0: 0, 1: 0, 2: 0, 3: 0, "4+": 0}
    for student_id in students:
        count = counts.get(student_id, 0)
        if count >= 4:
            distribution["4+"] += 1
        else:
            distribution[count] += 1
    data = [ChartDataPoint(name=str(k), value=v) for k, v in distribution.items()]
    return MultipleOffersResponse(data=data)
