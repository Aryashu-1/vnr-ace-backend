import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.placement_policy import PlacementPolicy
from models.placement_drive import PlacementDrive
from models.company import Company

router = APIRouter(prefix="", tags=["Admin Policies & Links"])

class PolicyCreateRequest(BaseModel):
    title: str
    description: str
    is_active: bool = True

@router.get("/policies")
async def get_policies(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(PlacementPolicy)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("/policies")
async def create_policy(
    body: PolicyCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    policy = PlacementPolicy(
        id=uuid.uuid4(),
        title=body.title,
        description=body.description,
        is_active=body.is_active
    )
    db.add(policy)
    await db.commit()
    await db.refresh(policy)
    return policy

@router.get("/external-links")
async def get_external_links(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    # Returns links from all active drives that require external registration
    query = select(PlacementDrive, Company).join(Company, PlacementDrive.company_id == Company.id).where(PlacementDrive.requires_external_registration == True)
    result = await db.execute(query)
    links = []
    for drive, company in result:
        links.append({
            "drive_id": drive.id,
            "company_name": company.name,
            "role": drive.role,
            "url": drive.external_registration_url
        })
    return links

@router.post("/external-links")
async def manage_external_link(
    drive_id: uuid.UUID,
    url: str,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    drive = await db.get(PlacementDrive, drive_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Drive not found")
    
    drive.external_registration_url = url
    drive.requires_external_registration = True
    await db.commit()
    return {"status": "success"}
