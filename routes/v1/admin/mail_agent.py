from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from typing import List
from core.db import get_db
from models.email_template import EmailTemplate
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/mail-agent", tags=["Admin Mail Agent"])

class EmailTemplateSchema(BaseModel):
    name: str
    subject: str
    body: str

class EmailTemplateResponse(EmailTemplateSchema):
    id: str
    last_used_at: datetime | None

    class Config:
        from_attributes = True

@router.get("/templates", response_model=List[EmailTemplateResponse])
async def get_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(EmailTemplate).order_by(EmailTemplate.name))
    return result.scalars().all()

@router.post("/templates")
async def create_or_update_template(
    payload: EmailTemplateSchema,
    template_id: str | None = None,
    db: AsyncSession = Depends(get_db)
):
    if template_id:
        template = await db.get(EmailTemplate, template_id)
        if not template:
            raise HTTPException(status_code=404, detail="Template not found")
        template.name = payload.name
        template.subject = payload.subject
        template.body = payload.body
    else:
        template = EmailTemplate(
            name=payload.name,
            subject=payload.subject,
            body=payload.body
        )
        db.add(template)
    
    await db.commit()
    return {"status": "success", "id": template.id}

@router.delete("/templates/{template_id}")
async def delete_template(template_id: str, db: AsyncSession = Depends(get_db)):
    await db.execute(delete(EmailTemplate).where(EmailTemplate.id == template_id))
    await db.commit()
    return {"status": "success"}
