from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class ResumeAnalysisCache(Base):
    __tablename__ = "resume_analysis_cache"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id"), nullable=False, index=True)
    analysis = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
