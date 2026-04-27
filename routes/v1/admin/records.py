import uuid
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
import pandas as pd

from core.db import get_db
from core.deps import role_required
from models.placement import Placement
from models.student import Student
from models.company import Company
from models.profile import Profile

router = APIRouter(prefix="/placement-records", tags=["Admin Placement Records"])

@router.get("")
async def list_placement_records(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(Placement, Student, Company, Profile).join(Student, Placement.student_id == Student.id).join(Company, Placement.company_id == Company.id).join(Profile, Student.profile_id == Profile.id)
    result = await db.execute(query)
    records = []
    for placement, student, company, profile in result:
        records.append({
            "id": placement.id,
            "student_name": profile.full_name,
            "roll_number": student.roll_no,
            "company_name": company.name,
            "ctc": placement.ctc_lpa,
            "date": placement.placement_date,
            "is_internship": placement.is_internship
        })
    return records

@router.post("/bulk")
async def bulk_upload_records(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if not file.filename.endswith(('.csv', '.xlsx')):
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload CSV or Excel.")

    contents = await file.read()
    if file.filename.endswith('.csv'):
        df = pd.read_csv(io.BytesIO(contents))
    else:
        df = pd.read_excel(io.BytesIO(contents))

    # Expected columns: roll_number, company_name, ctc, date, is_internship
    required_cols = ['roll_number', 'company_name', 'ctc']
    for col in required_cols:
        if col not in df.columns:
            raise HTTPException(status_code=400, detail=f"Missing required column: {col}")

    count = 0
    for _, row in df.iterrows():
        # 1. Find Student
        student = await db.scalar(select(Student).where(Student.roll_no == str(row['roll_number'])))
        if not student:
            continue
        
        # 2. Find/Create Company
        company = await db.scalar(select(Company).where(Company.name == str(row['company_name'])))
        if not company:
            company = Company(id=uuid.uuid4(), name=str(row['company_name']))
            db.add(company)
            await db.flush()

        # 3. Create Placement
        placement = Placement(
            student_id=student.id,
            company_id=company.id,
            ctc_lpa=float(row['ctc']),
            is_internship=bool(row.get('is_internship', False))
        )
        db.add(placement)
        count += 1

    await db.commit()
    return {"status": "success", "inserted_count": count}

@router.delete("/{id}")
async def delete_placement_record(
    id: int,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    placement = await db.get(Placement, id)
    if not placement:
        raise HTTPException(status_code=404, detail="Record not found")
    
    await db.delete(placement)
    await db.commit()
    return {"status": "success"}
