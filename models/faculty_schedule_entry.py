from sqlalchemy import Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class FacultyScheduleEntry(Base):
    __tablename__ = "faculty_schedule_entries"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    faculty_id = Column(UUID(as_uuid=True), ForeignKey("faculty.id"), nullable=False, index=True)
    day = Column(String, nullable=False, index=True)
    time_range = Column(String, nullable=False)
    activity = Column(Text, nullable=True)
    source = Column(String, nullable=True, default="ingestion")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
