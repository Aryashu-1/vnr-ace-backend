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
        await db.execute(select(Student.branch, func.count(Student.id)).group_by(Student.branch))
    ).all()
    placed_rows = (
        await db.execute(
            select(Student.branch, func.count(func.distinct(Student.id)))
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .group_by(Student.branch)
        )
    ).all()
    placed_map = {branch: count for branch, count in placed_rows}
    result = []
    for branch, total in total_rows:
        placed = placed_map.get(branch, 0)
        result.append({
            "name": branch or "UNKNOWN",
            "value": placed,
            "total": total,
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
You are an intelligent router for a placement dashboard. The user is asking for a specific chart or data visualization.
Match the user's query to one of the following available chart identifiers:
- placement-trend : Shows the trend of placements over years/months.
- branch-wise : Shows total vs placed students and percentage per branch.
- salary-distribution : Shows how salaries are distributed into buckets (<5, 5-10, 10-15, >15 LPA).
- company-wise : Shows the top hiring companies and placement counts.
- minor-degree : Shows the impact of having a minor degree on placements.
- multiple-offers : Shows the count of students with multiple offers.

If the user's query matches one of these, reply with ONLY the exact identifier name from the list above. Do not include quotes, periods, or formatting.
If the query does not match any of these charts, reply with ONLY the word: unknown

User Query: {query}
"""

async def _process_dynamic_chart(query: str, db: AsyncSession):
    try:
        llm = get_llm(temperature=0)
    except ValueError as e:
        raise HTTPException(status_code=500, detail=str(e))

    prompt_template = PromptTemplate(template=CHART_PROMPT, input_variables=["query"])
    chain = prompt_template | llm
    
    try:
        response = await chain.ainvoke({"query": query})
        identifier = response.content.strip().lower()
        
        if identifier == "placement-trend":
            data = await get_placement_trend(db)
            return {"chart": "placement-trend", "data": data}
        elif identifier == "branch-wise":
            data = await get_branch_wise_stats(db)
            return {"chart": "branch-wise", "data": data}
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
        raise HTTPException(status_code=500, detail=str(e))

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
