from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, JSON, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class Resume(Base):
    __tablename__ = "resumes"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), nullable=True, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=True, index=True)
    file_url = Column(String, nullable=True)
    raw_text = Column(Text, nullable=True)
    extracted_text = Column(Text, nullable=True)
    structured_json = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    current_version_id = Column(BigInteger, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
