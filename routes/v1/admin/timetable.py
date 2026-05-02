import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required
from models.timetable_entry import TimetableEntry

router = APIRouter(prefix="/timetable", tags=["Admin Timetable"])

class TimetableCreateUpdate(BaseModel):
    day: str
    start_time: str
    end_time: str
    subject: str
    room: Optional[str] = None
    faculty: Optional[str] = None
    section: str

@router.get("", response_model=List[dict])
async def list_timetable(
    day: Optional[str] = None,
    section: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    query = select(TimetableEntry)
    if day:
        query = query.filter(TimetableEntry.day == day)
    if section:
        query = query.filter(TimetableEntry.section == section)
    
    result = await db.execute(query.order_by(TimetableEntry.day, TimetableEntry.start_time))
    entries = result.scalars().all()
    
    return [
        {
            "id": str(e.id),
            "day": e.day,
            "startTime": e.start_time,
            "endTime": e.end_time,
            "subject": e.subject,
            "room": e.room,
            "faculty": e.faculty,
            "section": e.section
        } for e in entries
    ]

@router.post("")
async def create_or_update_timetable(
    body: TimetableCreateUpdate,
    entry_id: Optional[uuid.UUID] = None,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    if entry_id:
        entry = await db.get(TimetableEntry, entry_id)
        if not entry:
            raise HTTPException(status_code=404, detail="Entry not found")
        
        entry.day = body.day
        entry.start_time = body.start_time
        entry.end_time = body.end_time
        entry.subject = body.subject
        entry.room = body.room
        entry.faculty = body.faculty
        entry.section = body.section
    else:
        entry = TimetableEntry(
            id=uuid.uuid4(),
            day=body.day,
            start_time=body.start_time,
            end_time=body.end_time,
            subject=body.subject,
            room=body.room,
            faculty=body.faculty,
            section=body.section
        )
        db.add(entry)
    
    await db.commit()
    return {"status": "success", "id": str(entry.id)}

@router.delete("/{entry_id}")
async def delete_timetable_entry(
    entry_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    admin = Depends(role_required("admin"))
):
    entry = await db.get(TimetableEntry, entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    await db.delete(entry)
    await db.commit()
    return {"status": "success"}
