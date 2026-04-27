import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from core.db import get_db
from core.deps import role_required
from models.company import Company
from models.placement_drive import PlacementDrive

router = APIRouter(prefix="/companies", tags=["Admin Companies"])

class DriveCriteria(BaseModel):
    cgpa: float
    branches: List[str]
    backlogs: str

class CompanyDriveCreateRequest(BaseModel):
    name: str
    role: str
    ctc: Optional[str] = None
    deadline: Optional[date] = None
    criteria: Optional[DriveCriteria] = None
    requires_external_registration: bool = False
    external_registration_url: Optional[str] = None

class CompanyResponse(BaseModel):
    id: uuid.UUID
    name: str
    role: str
    ctc: Optional[float] = None
    deadline: Optional[date] = None
    status: str
    
    class Config:
        from_attributes = True

@router.get("")
async def list_company_drives(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(PlacementDrive, Company).join(Company, PlacementDrive.company_id == Company.id)
    result = await db.execute(query)
    drives = []
    for drive, company in result:
        drives.append({
            "id": drive.id,
            "company_id": company.id,
            "name": company.name,
            "role": drive.role,
            "ctc": drive.ctc,
            "deadline": drive.deadline,
            "status": drive.status,
            "requires_external_registration": drive.requires_external_registration,
            "external_registration_url": drive.external_registration_url,
            "criteria": drive.criteria
        })
    return drives

@router.post("")
async def register_company_drive(
    body: CompanyDriveCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    # 1. Get or Create Company
    query = select(Company).where(Company.name == body.name)
    company = await db.scalar(query)
    if not company:
        company = Company(id=uuid.uuid4(), name=body.name)
        db.add(company)
        await db.flush() # Get company ID
    
    # 2. Create Drive
    # Convert CTC string like "18 LPA" to float if possible, or just store as string if we change model
    # For now, PlacementDrive.ctc is Float. Let's try to extract float.
    ctc_val = None
    if body.ctc:
        import re
        match = re.search(r"(\d+\.?\d*)", body.ctc)
        if match:
            ctc_val = float(match.group(1))

    drive = PlacementDrive(
        id=uuid.uuid4(),
        company_id=company.id,
        role=body.role,
        ctc=ctc_val,
        deadline=body.deadline,
        criteria=body.criteria.dict() if body.criteria else None,
        requires_external_registration=body.requires_external_registration,
        external_registration_url=body.external_registration_url,
        status="open"
    )
    db.add(drive)
    await db.commit()
    return {"status": "success", "drive_id": str(drive.id)}

@router.put("/{id}")
async def update_company_drive(
    id: uuid.UUID,
    body: CompanyDriveCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    drive = await db.get(PlacementDrive, id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    # Update company name if changed (Careful here, might affect other drives)
    company = await db.get(Company, drive.company_id)
    if company and company.name != body.name:
        company.name = body.name

    ctc_val = None
    if body.ctc:
        import re
        match = re.search(r"(\d+\.?\d*)", body.ctc)
        if match:
            ctc_val = float(match.group(1))

    drive.role = body.role
    drive.ctc = ctc_val
    drive.deadline = body.deadline
    drive.criteria = body.criteria.dict() if body.criteria else None
    drive.requires_external_registration = body.requires_external_registration
    drive.external_registration_url = body.external_registration_url
    
    await db.commit()
    return {"status": "success"}

@router.delete("/{id}")
async def delete_company_drive(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    drive = await db.get(PlacementDrive, id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    await db.delete(drive)
    await db.commit()
    return {"status": "success"}
