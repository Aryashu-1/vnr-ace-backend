from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from core.db import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    user_type = Column(String, nullable=False)
    status = Column(String, default="active")
    hashed_password = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    roles = relationship("UserRole", back_populates="profile", cascade="all, delete-orphan")
    student_profile = relationship("Student", back_populates="profile", uselist=False)
    faculty_profile = relationship("Faculty", back_populates="profile", uselist=False)
