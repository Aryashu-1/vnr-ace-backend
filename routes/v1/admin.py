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

class RegistrationVerifyRequest(BaseModel):
    application_ids: List[str]
    status: str # 'verified', 'rejected'

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

@router.post("/verify-student-registration")
async def verify_student_registration(
    body: RegistrationVerifyRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    # Bulk update applications
    for app_id in body.application_ids:
        app = await db.get(PlacementApplication, app_id)
        if app:
            if body.status == "verified":
                app.status = "applied" # Once verified, it becomes a normal 'applied' status
            else:
                app.status = "external_rejected"
    
    await db.commit()
    return {"status": "success", "message": f"Updated {len(body.application_ids)} applications"}
