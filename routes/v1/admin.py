import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.placement_drive import PlacementDrive
from models.placement_application import PlacementApplication

router = APIRouter(prefix="/admin/placements", tags=["Admin Placements"])

class JobCreateUpdateRequest(BaseModel):
    company_id: uuid.UUID
    role: str
    ctc: Optional[float] = None
    status: Optional[str] = "open"
    external_registration_url: Optional[str] = None
    requires_external_registration: bool = False

class CompanyCreateUpdateRequest(BaseModel):
    name: str
    sector: Optional[str] = None
    domain: Optional[str] = None

class RegistrationVerifyRequest(BaseModel):
    application_ids: List[str]
    status: str # 'verified', 'rejected'

from models.company import Company

# --- Company Management ---

@router.get("/companies")
async def list_companies(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    result = await db.execute(select(Company).order_by(Company.name))
    return result.scalars().all()

@router.post("/companies")
async def create_or_update_company(
    body: CompanyCreateUpdateRequest,
    company_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if company_id:
        company = await db.get(Company, company_id)
        if not company:
            raise HTTPException(status_code=404, detail="Company not found")
        company.name = body.name
        company.sector = body.sector
        company.domain = body.domain
    else:
        company = Company(
            id=uuid.uuid4(),
            name=body.name,
            sector=body.sector,
            domain=body.domain
        )
        db.add(company)
    
    await db.commit()
    await db.refresh(company)
    return {"status": "success", "company": company}

@router.delete("/companies/{company_id}")
async def delete_company(
    company_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    company = await db.get(Company, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")
    
    await db.delete(company)
    await db.commit()
    return {"status": "success"}

# --- Job/Drive Management ---

@router.get("/jobs")
async def list_jobs_admin(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    from sqlalchemy.orm import joinedload
    result = await db.execute(
        select(PlacementDrive).options(joinedload(PlacementDrive.company_rel)).order_by(PlacementDrive.created_at.desc())
    )
    drives = result.scalars().all()
    return [{
        "id": str(d.id),
        "company_id": str(d.company_id),
        "company_name": d.company_rel.name if d.company_rel else "Unknown",
        "role": d.role,
        "ctc": d.ctc,
        "status": d.status,
        "deadline": d.created_at.strftime("%Y-%m-%d") if d.created_at else None,
        "requires_external_registration": d.requires_external_registration,
        "external_registration_url": d.external_registration_url
    } for d in drives]

@router.post("/jobs")
async def create_or_update_job(
    body: JobCreateUpdateRequest,
    job_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if job_id:
        drive = await db.get(PlacementDrive, job_id)
        if not drive:
            raise HTTPException(status_code=404, detail="Job not found")
        
        drive.company_id = body.company_id
        drive.role = body.role
        drive.ctc = body.ctc
        drive.status = body.status
        drive.external_registration_url = body.external_registration_url
        drive.requires_external_registration = body.requires_external_registration
    else:
        drive = PlacementDrive(
            id=uuid.uuid4(),
            company_id=body.company_id,
            role=body.role,
            ctc=body.ctc,
            status=body.status,
            external_registration_url=body.external_registration_url,
            requires_external_registration=body.requires_external_registration
        )
        db.add(drive)
    
    await db.commit()
    return {"status": "success", "job_id": str(drive.id)}

@router.delete("/jobs/{job_id}")
async def delete_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    drive = await db.get(PlacementDrive, job_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Job not found")
    
    await db.delete(drive)
    await db.commit()
    return {"status": "success"}

@router.get("/applications")
async def list_applications_admin(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    from sqlalchemy.orm import joinedload
    from models.student import Student
    from models.profile import Profile
    from models.company import Company

    query = (
        select(PlacementApplication)
        .options(
            joinedload(PlacementApplication.student_rel).joinedload(Student.profile),
            joinedload(PlacementApplication.drive_rel).joinedload(PlacementDrive.company_rel)
        )
        .order_by(PlacementApplication.created_at.desc())
    )
    result = await db.execute(query)
    apps = result.scalars().all()
    
    return [{
        "id": str(a.id),
        "student_name": a.student_rel.profile.full_name if a.student_rel and a.student_rel.profile else "Unknown",
        "roll_no": a.student_rel.roll_no if a.student_rel else "N/A",
        "company": a.drive_rel.company_rel.name if a.drive_rel and a.drive_rel.company_rel else "Unknown",
        "package": f"{a.drive_rel.ctc} LPA" if a.drive_rel and a.drive_rel.ctc else "-",
        "status": a.status,
        "date": a.created_at.strftime("%Y-%m-%d") if a.created_at else None
    } for a in apps]

@router.post("/verify-student-registration")
async def verify_student_registration(
    body: RegistrationVerifyRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    for app_id in body.application_ids:
        app = await db.get(PlacementApplication, app_id)
        if app:
            if body.status == "verified":
                app.status = "applied"
            else:
                app.status = "external_rejected"
    
    await db.commit()
    return {"status": "success", "message": f"Updated {len(body.application_ids)} applications"}
