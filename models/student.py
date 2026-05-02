from typing import Optional
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base

class Student(Base):
    __tablename__ = "students"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    roll_no = Column(String, unique=True, index=True, nullable=False)
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True, index=True)
    department_id = Column(UUID(as_uuid=True), ForeignKey("departments.id"), nullable=True)
    
    gender = Column(String, nullable=True)
    dob = Column(String, nullable=True) # Or Date depending on exact need
    section = Column(String, nullable=True)
    current_year = Column(Integer, nullable=True)
    
    cgpa = Column(Float, nullable=True)
    backlogs = Column(Integer, nullable=True, default=0)
    tenth_cgpa = Column(Float, nullable=True)
    inter_percent = Column(Float, nullable=True)
    active_backlogs = Column(Integer, nullable=True, default=0)
    passive_backlogs = Column(Integer, nullable=True, default=0)
    
    category = Column(String, nullable=True)
    home_town = Column(String, nullable=True)
    district = Column(String, nullable=True)
    state = Column(String, nullable=True)
    pincode = Column(String, nullable=True)
    
    minor_degree = Column(String, nullable=True)
    intern_status = Column(Boolean, nullable=True, default=False)
    placement_status = Column(String, index=True, nullable=True, default="unplaced")
    highest_package = Column(Float, nullable=True, default=0.0)
    total_offers = Column(Integer, nullable=True, default=0)
    attendance = Column(Float, nullable=True, default=0.0)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    profile = relationship("Profile", back_populates="student_profile")
    department_rel = relationship("Department")
    interview_experiences = relationship("InterviewExperience", back_populates="student")

    @property
    def branch(self) -> Optional[str]:
        return self.department_rel.name if self.department_rel else None

    @property
    def full_name(self) -> Optional[str]:
        return self.profile.full_name if self.profile else None
