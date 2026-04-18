from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, JSON, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class ResumeVersion(Base):
    __tablename__ = "resume_versions"
    __table_args__ = (
        UniqueConstraint("resume_id", "version_number", name="uq_resume_versions_resume_version"),
    )

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    resume_id = Column(UUID(as_uuid=True), ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    version_number = Column(Integer, nullable=False)
    content = Column(JSON, nullable=False)
    change_summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
