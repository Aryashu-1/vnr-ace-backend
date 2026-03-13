from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON
from sqlalchemy.sql import func
from core.db import Base

class JobNotification(Base):
    __tablename__ = "job_notifications"

    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    role = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    
    # Eligibility Criteria
    min_cgpa = Column(Float, nullable=True)
    min_tenth_cgpa = Column(Float, nullable=True)
    min_inter_percent = Column(Float, nullable=True)
    max_active_backlogs = Column(Integer, nullable=True)
    max_passive_backlogs = Column(Integer, nullable=True)
    allowed_branches = Column(JSON, nullable=True) # e.g., ["CSE", "IT"]
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
