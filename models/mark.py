from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class Mark(Base):
    __tablename__ = "marks"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    subject = Column(String, nullable=False, index=True)
    internal = Column(Float, nullable=True)
    external = Column(Float, nullable=True)
    total = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
