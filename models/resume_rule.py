from sqlalchemy import Column, String, Integer, DateTime, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.db import Base

class ResumeRule(Base):
    __tablename__ = "resume_rules"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False)
    category = Column(String, nullable=False) # e.g., "Keyword", "Formatting"
    weight = Column(Integer, nullable=False, default=10) # 0-100
    description = Column(String, nullable=True)
    required_keywords = Column(JSON, nullable=True) # List of keywords
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
