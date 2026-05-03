from datetime import datetime
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from core.db import get_db
from core.llm import get_llm
from models.company import Company
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.student import Student
from models.department import Department

router = APIRouter(prefix="/charts", tags=["Charts API"])

@router.get("/placement-trend")
async def get_placement_trend(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(extract("year", PlacementDrive.drive_date).label("year"), func.count(PlacementOfferV2.id))
            .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
            .where(PlacementDrive.drive_date.is_not(None))
            .group_by("year")
            .order_by("year")
        )
    ).all()
    return [{"name": str(int(year)), "value": count} for year, count in rows if year is not None]

@router.get("/branch-wise")
async def get_branch_wise_stats(db: AsyncSession = Depends(get_db)):
    total_rows = (
        await db.execute(
            select(Department.name, func.count(Student.id))
            .join(Department, Student.department_id == Department.id)
            .group_by(Department.name)
        )
    ).all()
    
    # Get placed counts and average salary
    placed_stats = (
        await db.execute(
            select(Department.name, func.count(func.distinct(Student.id)), func.avg(PlacementOfferV2.offered_ctc))
            .join(Student, Student.department_id == Department.id)
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .group_by(Department.name)
        )
    ).all()
    
    stats_map = {branch: (count, avg) for branch, count, avg in placed_stats}
    result = []
    for branch, total in total_rows:
        placed, avg_salary = stats_map.get(branch, (0, 0))
        result.append({
            "name": branch or "UNKNOWN",
            "value": placed, # Number of students placed
            "total": total,
            "avg_salary": round(avg_salary or 0, 2),
            "percentage": round((placed / total * 100), 2) if total else 0,
        })
    return result

@router.get("/salary-distribution")
async def get_salary_distribution(db: AsyncSession = Depends(get_db)):
    buckets = {"< 5 LPA": 0, "5 - 10 LPA": 0, "10 - 15 LPA": 0, "> 15 LPA": 0}
    rows = (await db.execute(select(PlacementOfferV2.offered_ctc))).scalars().all()
    for s in rows:
        if s is None: continue
        if s < 5: buckets["< 5 LPA"] += 1
        elif s < 10: buckets["5 - 10 LPA"] += 1
        elif s < 15: buckets["10 - 15 LPA"] += 1
        else: buckets["> 15 LPA"] += 1
            
    return [{"name": k, "value": v} for k, v in buckets.items()]

@router.get("/company-wise")
async def get_company_wise_stats(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(Company.name, func.count(PlacementOfferV2.id))
            .join(PlacementDrive, PlacementDrive.company_id == Company.id)
            .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
            .group_by(Company.name)
            .order_by(func.count(PlacementOfferV2.id).desc())
            .limit(10)
        )
    ).all()
    return [{"name": name, "value": count} for name, count in rows]

@router.get("/minor-degree")
async def get_minor_degree_stats(db: AsyncSession = Depends(get_db)):
    with_minor = (await db.execute(select(func.count(Student.id)).where(Student.minor_degree.is_not(None)))).scalar() or 0
    without_minor = (await db.execute(select(func.count(Student.id)).where(Student.minor_degree.is_(None)))).scalar() or 0
    with_minor_placed = (
        await db.execute(
            select(func.count(func.distinct(Student.id)))
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .where(Student.minor_degree.is_not(None))
        )
    ).scalar() or 0
    without_minor_placed = (
        await db.execute(
            select(func.count(func.distinct(Student.id)))
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .where(Student.minor_degree.is_(None))
        )
    ).scalar() or 0
    return [
        {"name": "With Minor", "value": with_minor_placed, "total": with_minor},
        {"name": "Without Minor", "value": without_minor_placed, "total": without_minor}
    ]

@router.get("/multiple-offers")
async def get_multiple_offers(db: AsyncSession = Depends(get_db)):
    rows = (
        await db.execute(
            select(PlacementOfferV2.student_id, func.count(PlacementOfferV2.id)).group_by(PlacementOfferV2.student_id)
        )
    ).all()
    multiple = len([student_id for student_id, count in rows if count > 1])
    single = len([student_id for student_id, count in rows if count == 1])
    return [
        {"name": "Multiple Offers", "value": multiple},
        {"name": "Single Offer", "value": single}
    ]

class ChartQueryRequest(BaseModel):
    query: str

CHART_PROMPT = """
You are an expert AI data router for a VNR-ACE placement dashboard. Your job is to classify the user's natural language request into the most appropriate chart identifier.

Available Charts:
1. placement-trend : Yearly/Monthly hiring trends. (Keywords: trend, over time, years, progress)
2. branch-wise : Statistics per branch/department, including placement counts. (Keywords: branch, department, cse, ece, it, branch performance)
3. salary-distribution : Global salary ranges and buckets. (Keywords: salary range, buckets, distribution, package spread)
4. branch-salary : Average salary comparison between branches. (Keywords: average salary per branch, branch salary, which branch gets highest pay, cse avg package, package per department)
5. company-wise : Top companies by hiring volume. (Keywords: top companies, who hired most, company stats)
6. minor-degree : Success rate of students with vs without minor degrees. (Keywords: minor degree, impact of minor)
7. multiple-offers : Count of students who secured more than one job. (Keywords: dual offers, 2+ jobs, multiple placements)

Classification Rules:
- If the user asks for "average salary of branches" or "package per department", use 'branch-salary'.
- If they ask for "how many placed in CSE", use 'branch-wise'.
- If they ask for "salary distribution" or "package buckets", use 'salary-distribution'.
- Reply with ONLY the exact identifier name (e.g., 'branch-wise').
- If no match is found, reply with 'unknown'.

User Query: {query}
"""




async def _process_dynamic_chart(query: str, db: AsyncSession):
    from core.llm import call_llm
    
    prompt = CHART_PROMPT.format(query=query)
    
    try:
        response = await call_llm(prompt)
        identifier = response.strip().lower()
        
        if identifier == "placement-trend":
            data = await get_placement_trend(db)
            return {"chart": "placement-trend", "data": data}
        elif identifier == "branch-wise":
            data = await get_branch_wise_stats(db)
            return {"chart": "branch-wise", "data": data}
        elif identifier == "branch-salary":
            data = await get_branch_wise_stats(db)
            return {"chart": "branch-salary", "data": data}
        elif identifier == "salary-distribution":
            data = await get_salary_distribution(db)
            return {"chart": "salary-distribution", "data": data}
        elif identifier == "company-wise":
            data = await get_company_wise_stats(db)
            return {"chart": "company-wise", "data": data}
        elif identifier == "minor-degree":
            data = await get_minor_degree_stats(db)
            return {"chart": "minor-degree", "data": data}
        elif identifier == "multiple-offers":
            data = await get_multiple_offers(db)
            return {"chart": "multiple-offers", "data": data}
        else:
            return {"error": "Could not identify a matching chart.", "chart": "unknown"}
            
    except Exception as e:
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Chart Error: {str(e)}")

@router.get("/dynamic")
async def get_dynamic_chart(query: str, db: AsyncSession = Depends(get_db)):
    """
    Identify and return chart data based on a natural language text query (GET).
    """
    return await _process_dynamic_chart(query, db)

@router.post("/dynamic")
async def generate_dynamic_chart(request: ChartQueryRequest, db: AsyncSession = Depends(get_db)):
    """
    Identify and return chart data based on a natural language text query (POST).
    """
    return await _process_dynamic_chart(request.query, db)
