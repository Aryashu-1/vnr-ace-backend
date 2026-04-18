from sqlalchemy import Column, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from sqlalchemy.orm import relationship

from core.db import Base

class Faculty(Base):
    __tablename__ = "faculty"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True, index=True)
    department = Column(String, nullable=False, index=True)
    designation = Column(String, nullable=True)
    cabin = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    profile = relationship("Profile", back_populates="faculty_profile")
