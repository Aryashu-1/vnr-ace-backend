import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.faq import FAQ
from models.department import Department

router = APIRouter(prefix="/admissions", tags=["Admissions"])

class FAQCreateUpdate(BaseModel):
    question: str
    answer: str
    category: str

class DepartmentCreateUpdate(BaseModel):
    name: str
    code: Optional[str] = None
    intake: Optional[str] = None
    hod: Optional[str] = None
    description: Optional[str] = None

# --- Department Management ---

@router.get("/departments", response_model=List[dict])
async def list_departments(
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Department).order_by(Department.name))
    depts = result.scalars().all()
    return [
        {
            "id": str(d.id),
            "name": d.name,
            "code": d.code,
            "intake": d.intake,
            "hod": d.hod,
            "description": d.description
        } for d in depts
    ]

@router.post("/departments")
async def create_or_update_department(
    body: DepartmentCreateUpdate,
    dept_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if dept_id:
        dept = await db.get(Department, dept_id)
        if not dept:
            raise HTTPException(status_code=404, detail="Department not found")
        
        dept.name = body.name
        dept.code = body.code
        dept.intake = body.intake
        dept.hod = body.hod
        dept.description = body.description
    else:
        dept = Department(
            id=uuid.uuid4(),
            name=body.name,
            code=body.code,
            intake=body.intake,
            hod=body.hod,
            description=body.description
        )
        db.add(dept)
    
    await db.commit()
    return {"status": "success", "id": str(dept.id)}

@router.delete("/departments/{dept_id}")
async def delete_department(
    dept_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(status_code=404, detail="Department not found")
    
    await db.delete(dept)
    await db.commit()
    return {"status": "success"}

# --- FAQ Management ---

@router.get("/faqs", response_model=List[dict])
async def list_faqs(
    category: Optional[str] = None,
    db: AsyncSession = Depends(get_db)
):
    query = select(FAQ)
    if category:
        query = query.where(FAQ.category == category)
    
    result = await db.execute(query)
    faqs = result.scalars().all()
    return [
        {
            "id": str(f.id),
            "question": f.question,
            "answer": f.answer,
            "category": f.category
        } for f in faqs
    ]

@router.post("/faqs")
async def create_or_update_faq(
    body: FAQCreateUpdate,
    faq_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if faq_id:
        faq = await db.get(FAQ, faq_id)
        if not faq:
            raise HTTPException(status_code=404, detail="FAQ not found")
        
        faq.question = body.question
        faq.answer = body.answer
        faq.category = body.category
    else:
        faq = FAQ(
            id=uuid.uuid4(),
            question=body.question,
            answer=body.answer,
            category=body.category
        )
        db.add(faq)
    
    await db.commit()
    return {"status": "success", "id": str(faq.id)}

@router.delete("/faqs/{faq_id}")
async def delete_faq(
    faq_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    faq = await db.get(FAQ, faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    
    await db.delete(faq)
    await db.commit()
    return {"status": "success"}
