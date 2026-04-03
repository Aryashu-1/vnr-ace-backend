from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy import select
from core.db import get_db
import io
import csv

from models.student import Student
from models.placement import Placement
from models.company import Company

router = APIRouter(prefix="/export", tags=["Export API"])

@router.get("/students")
async def export_students_csv(db: AsyncSession = Depends(get_db)):
    students = (await db.execute(select(Student))).scalars().all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Roll No", "Name", "Branch", "CGPA"])
    for s in students:
        writer.writerow([s.id, s.roll_no, s.full_name, s.branch, s.cgpa])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=students.csv"}
    )

@router.get("/placements")
async def export_placements_csv(db: AsyncSession = Depends(get_db)):
    # Join Placements + Students + Companies
    query = select(Placement, Student.roll_no, Company.name).join(Student).join(Company)
    results = (await db.execute(query)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Placement ID", "Student Roll", "Company", "CTC (LPA)", "Date"])
    for p, roll, company in results:
        date_str = p.placement_date.strftime("%Y-%m-%d") if p.placement_date else "N/A"
        writer.writerow([p.id, roll, company, p.ctc_lpa, date_str])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=placements.csv"}
    )

@router.get("/dashboard")
async def export_dashboard_csv(db: AsyncSession = Depends(get_db)):
    # Exporting a simple stats summary
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    # Dummy data until actual stats service is wired here
    writer.writerow(["Export Status", "Success"])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dashboard_summary.csv"}
    )
