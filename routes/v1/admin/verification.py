import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.placement_application import PlacementApplication

router = APIRouter(prefix="/verification", tags=["Admin Verification"])

class RegistrationVerifyRequest(BaseModel):
    application_ids: List[str]
    status: str # 'verified', 'rejected'

@router.post("/student-registration")
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
