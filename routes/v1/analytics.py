import json
from pathlib import Path
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from core.db import get_db
from schemas.analytics import ChartDataPoint, PlacementTrendResponse, BranchWiseResponse, SalaryDistributionResponse, TopHiringResponse, MinorImpactResponse, MultipleOffersResponse
from models.student import Student
from models.placement import Placement
from models.company import Company

router = APIRouter(prefix="/analytics", tags=["Analytics"])

DATA_DIR = Path("data")
STUDENTS_FILE = DATA_DIR / "students_sample.json"
PLACEMENTS_FILE = DATA_DIR / "placements_sample.json"
COMPANIES_FILE = DATA_DIR / "companies_sample.json"

def load_local_data(file_path: Path):
    if not file_path.exists():
        return []
    with open(file_path, "r") as f:
        return json.load(f)

@router.get("/placement-trend", response_model=PlacementTrendResponse)
async def get_placement_trend(db: AsyncSession = Depends(get_db)):
    try:
        # Try DB first
        # result = await db.execute(select(func.extract('year', Placement.placement_date).label('year'), func.count(Placement.id)).group_by('year'))
        # ... logic for DB
        raise Exception("DB logic not fully implemented, falling back to local")
    except Exception:
        placements = load_local_data(PLACEMENTS_FILE)
        trends = {}
        for p in placements:
            date_str = p.get("placement_date")
            if date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                year = str(dt.year)
                trends[year] = trends.get(year, 0) + 1
        
        data = [ChartDataPoint(name=y, value=count) for y, count in sorted(trends.items())]
        return PlacementTrendResponse(data=data)

@router.get("/branch-wise", response_model=BranchWiseResponse)
async def get_branch_wise_stats(db: AsyncSession = Depends(get_db)):
    try:
        raise Exception("DB fallback")
    except Exception:
        students = load_local_data(STUDENTS_FILE)
        placements = load_local_data(PLACEMENTS_FILE)
        placed_ids = {p["student_id"] for p in placements}
        
        branch_stats = {}
        for s in students:
            branch = s.get("branch", "Other")
            if branch not in branch_stats:
                branch_stats[branch] = {"total": 0, "placed": 0}
            branch_stats[branch]["total"] += 1
            if s["id"] in placed_ids:
                branch_stats[branch]["placed"] += 1
        
        data = []
        for branch, stats in branch_stats.items():
            percentage = round((stats["placed"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0
            data.append(ChartDataPoint(name=branch, value=stats["placed"], total=stats["total"], percentage=percentage))
        
        return BranchWiseResponse(data=data)

@router.get("/salary-distribution", response_model=SalaryDistributionResponse)
async def get_salary_distribution(db: AsyncSession = Depends(get_db)):
    try:
        raise Exception("DB fallback")
    except Exception:
        placements = load_local_data(PLACEMENTS_FILE)
        buckets = {"0-5 LPA": 0, "5-10 LPA": 0, "10-15 LPA": 0, "15+ LPA": 0}
        for p in placements:
            ctc = p.get("ctc_lpa", 0)
            if ctc < 5: buckets["0-5 LPA"] += 1
            elif ctc < 10: buckets["5-10 LPA"] += 1
            elif ctc < 15: buckets["10-15 LPA"] += 1
            else: buckets["15+ LPA"] += 1
        
        data = [ChartDataPoint(name=k, value=v) for k, v in buckets.items()]
        return SalaryDistributionResponse(data=data)

@router.get("/top-hiring", response_model=TopHiringResponse)
async def get_top_hiring(db: AsyncSession = Depends(get_db)):
    try:
        raise Exception("DB fallback")
    except Exception:
        placements = load_local_data(PLACEMENTS_FILE)
        companies = load_local_data(COMPANIES_FILE)
        comp_map = {c["id"]: c["name"] for c in companies}
        
        hires = {}
        for p in placements:
            comp_name = comp_map.get(p["company_id"], "Unknown")
            hires[comp_name] = hires.get(comp_name, 0) + 1
        
        sorted_hires = sorted(hires.items(), key=lambda x: x[1], reverse=True)[:10]
        data = [ChartDataPoint(name=name, value=count) for name, count in sorted_hires]
        return TopHiringResponse(data=data)

@router.get("/minor-impact", response_model=MinorImpactResponse)
async def get_minor_impact(db: AsyncSession = Depends(get_db)):
    try:
        raise Exception("DB fallback")
    except Exception:
        students = load_local_data(STUDENTS_FILE)
        placements = load_local_data(PLACEMENTS_FILE)
        placed_ids = {p["student_id"] for p in placements}
        
        with_minor = [s for s in students if s.get("minor_degree")]
        without_minor = [s for s in students if not s.get("minor_degree")]
        
        placed_with = len([s for s in with_minor if s["id"] in placed_ids])
        placed_without = len([s for s in without_minor if s["id"] in placed_ids])
        
        data = [
            ChartDataPoint(name="With Minor", value=placed_with, total=len(with_minor)),
            ChartDataPoint(name="Without Minor", value=placed_without, total=len(without_minor))
        ]
        return MinorImpactResponse(data=data)

@router.get("/multiple-offers", response_model=MultipleOffersResponse)
async def get_multiple_offers(db: AsyncSession = Depends(get_db)):
    try:
        raise Exception("DB fallback")
    except Exception:
        students = load_local_data(STUDENTS_FILE)
        placements = load_local_data(PLACEMENTS_FILE)
        
        offer_counts = {}
        for p in placements:
            sid = p["student_id"]
            offer_counts[sid] = offer_counts.get(sid, 0) + 1
        
        distribution = {0: 0, 1: 0, 2: 0, 3: 0, "4+": 0}
        
        # All students (including those with 0 offers)
        for s in students:
            count = offer_counts.get(s["id"], 0)
            if count >= 4:
                distribution["4+"] += 1
            else:
                distribution[count] += 1
        
        data = [ChartDataPoint(name=str(k), value=v) for k, v in distribution.items()]
        return MultipleOffersResponse(data=data)
