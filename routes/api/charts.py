import os
import json
from pathlib import Path
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from langchain_core.prompts import PromptTemplate
from core.db import get_db
from core.llm import get_llm

DATA_DIR = Path("data")
STUDENTS_FILE = DATA_DIR / "students_sample.json"
PLACEMENTS_FILE = DATA_DIR / "placements_sample.json"
COMPANIES_FILE = DATA_DIR / "companies_sample.json"

def load_local_data(file_path):
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)

router = APIRouter(prefix="/charts", tags=["Charts API"])

@router.get("/placement-trend")
async def get_placement_trend(db: AsyncSession = Depends(get_db)):
    placements = load_local_data(PLACEMENTS_FILE)
    trends = {}
    for p in placements:
        p_date_str = p.get("placement_date")
        if p_date_str:
            try:
                # Handle ISO format
                dt = datetime.fromisoformat(p_date_str.replace('Z', '+00:00'))
                year = dt.year
                trends[year] = trends.get(year, 0) + 1
            except:
                continue
            
    result = [{"name": str(y), "value": count} for y, count in sorted(trends.items())]
    return result

@router.get("/branch-wise")
async def get_branch_wise_stats(db: AsyncSession = Depends(get_db)):
    students = load_local_data(STUDENTS_FILE)
    placements = load_local_data(PLACEMENTS_FILE)
    
    # Map student_id to whether they are placed
    placed_student_ids = {p["student_id"] for p in placements}
    
    branch_stats = {}
    for s in students:
        branch = s.get("branch", "UNKNOWN")
        if branch not in branch_stats:
            branch_stats[branch] = {"total": 0, "placed": 0}
        
        branch_stats[branch]["total"] += 1
        if s["id"] in placed_student_ids:
            branch_stats[branch]["placed"] += 1
            
    result = []
    for branch, stats in branch_stats.items():
        total = stats["total"]
        placed = stats["placed"]
        percentage = round((placed / total * 100), 2) if total > 0 else 0
        result.append({
            "name": branch,
            "value": placed,
            "total": total,
            "percentage": percentage
        })
    return result

@router.get("/salary-distribution")
async def get_salary_distribution(db: AsyncSession = Depends(get_db)):
    placements = load_local_data(PLACEMENTS_FILE)
    buckets = {"< 5 LPA": 0, "5 - 10 LPA": 0, "10 - 15 LPA": 0, "> 15 LPA": 0}
    
    for p in placements:
        s = p.get("ctc_lpa")
        if s is None: continue
        if s < 5: buckets["< 5 LPA"] += 1
        elif s < 10: buckets["5 - 10 LPA"] += 1
        elif s < 15: buckets["10 - 15 LPA"] += 1
        else: buckets["> 15 LPA"] += 1
            
    return [{"name": k, "value": v} for k, v in buckets.items()]

@router.get("/company-wise")
async def get_company_wise_stats(db: AsyncSession = Depends(get_db)):
    placements = load_local_data(PLACEMENTS_FILE)
    companies = load_local_data(COMPANIES_FILE)
    
    comp_map = {c["id"]: c["name"] for c in companies}
    hires = {}
    for p in placements:
        cid = p.get("company_id")
        name = comp_map.get(cid, "Unknown")
        hires[name] = hires.get(name, 0) + 1
        
    sorted_hires = sorted(hires.items(), key=lambda x: x[1], reverse=True)[:10]
    return [{"name": name, "value": count} for name, count in sorted_hires]

@router.get("/minor-degree")
async def get_minor_degree_stats(db: AsyncSession = Depends(get_db)):
    students = load_local_data(STUDENTS_FILE)
    placements = load_local_data(PLACEMENTS_FILE)
    placed_ids = {p["student_id"] for p in placements}
    
    with_minor = [s for s in students if s.get("minor_degree")]
    without_minor = [s for s in students if not s.get("minor_degree")]
    
    with_minor_placed = len([s for s in with_minor if s["id"] in placed_ids])
    without_minor_placed = len([s for s in without_minor if s["id"] in placed_ids])
    
    return [
        {"name": "With Minor", "value": with_minor_placed, "total": len(with_minor)},
        {"name": "Without Minor", "value": without_minor_placed, "total": len(without_minor)}
    ]

@router.get("/multiple-offers")
async def get_multiple_offers(db: AsyncSession = Depends(get_db)):
    placements = load_local_data(PLACEMENTS_FILE)
    
    student_counts = {}
    for p in placements:
        sid = p["student_id"]
        student_counts[sid] = student_counts.get(sid, 0) + 1
        
    multiple = len([sid for sid, count in student_counts.items() if count > 1])
    single = len([sid for sid, count in student_counts.items() if count == 1])
    
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
