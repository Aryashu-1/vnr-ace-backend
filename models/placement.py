from sqlalchemy import Column, Integer, Float, Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base

class Placement(Base):
    __tablename__ = "placements"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    
    ctc_lpa = Column(Float, nullable=True, index=True)
    placement_date = Column(DateTime(timezone=True), nullable=True)  # Or Date
    is_internship = Column(Boolean, nullable=True, default=False)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    student = relationship("Student")
    company = relationship("Company")
