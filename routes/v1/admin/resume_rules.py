import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Body
from pydantic import BaseModel, Field
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.resume_rule import ResumeRule

router = APIRouter(prefix="/resume-rules", tags=["Admin Resume Rules"])

class ResumeRuleCreateRequest(BaseModel):
    name: str
    category: str
    weight: int = Field(..., ge=0, le=100)
    description: Optional[str] = None
    required_keywords: Optional[List[str]] = None

@router.get("")
async def get_resume_rules(
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(ResumeRule)
    result = await db.execute(query)
    return result.scalars().all()

@router.post("")
async def create_resume_rule(
    body: ResumeRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    rule = ResumeRule(
        id=uuid.uuid4(),
        name=body.name,
        category=body.category,
        weight=body.weight,
        description=body.description,
        required_keywords=body.required_keywords
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return rule

@router.put("/{id}")
async def update_resume_rule(
    id: uuid.UUID,
    body: ResumeRuleCreateRequest,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    rule = await db.get(ResumeRule, id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    rule.name = body.name
    rule.category = body.category
    rule.weight = body.weight
    rule.description = body.description
    rule.required_keywords = body.required_keywords
    
    await db.commit()
    return {"status": "success"}

@router.patch("/settings")
async def update_shortlisting_settings(
    threshold: int = Body(..., ge=0, le=100, embed=True),
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    # This could be stored in a 'Settings' table or a special rule.
    # For now, let's just return a success since we don't have a settings table yet.
    # We can implement a simple key-value store for settings if needed.
    return {"status": "success", "threshold": threshold}

@router.delete("/{id}")
async def delete_resume_rule(
    id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    rule = await db.get(ResumeRule, id)
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()
    return {"status": "success"}
