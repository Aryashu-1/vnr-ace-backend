from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from core.db import get_db
import io
import csv

from models.student import Student
from models.company import Company
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.dashboard_snapshot import DashboardSnapshot

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
    query = (
        select(PlacementOfferV2.id, Student.roll_no, Company.name, PlacementOfferV2.offered_ctc, PlacementDrive.drive_date)
        .join(Student, Student.id == PlacementOfferV2.student_id)
        .join(PlacementDrive, PlacementDrive.id == PlacementOfferV2.drive_id)
        .join(Company, Company.id == PlacementDrive.company_id)
    )
    results = (await db.execute(query)).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Placement ID", "Student Roll", "Company", "CTC (LPA)", "Date"])
    for placement_id, roll, company, offered_ctc, drive_date in results:
        date_str = drive_date.strftime("%Y-%m-%d") if drive_date else "N/A"
        writer.writerow([placement_id, roll, company, offered_ctc, date_str])
        
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=placements.csv"}
    )

@router.get("/dashboard")
async def export_dashboard_csv(db: AsyncSession = Depends(get_db)):
    snapshot = (
        await db.execute(select(DashboardSnapshot).order_by(DashboardSnapshot.updated_at.desc()))
    ).scalars().first()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Metric", "Value"])
    if snapshot:
        writer.writerow(["Total Students", snapshot.total_students])
        writer.writerow(["Placed Students", snapshot.placed_students])
        writer.writerow(["Placement Rate", snapshot.placement_rate])
        writer.writerow(["Average Package", snapshot.avg_package])
    else:
        writer.writerow(["Export Status", "No snapshot found"])
    
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=dashboard_summary.csv"}
    )
