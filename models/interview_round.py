from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class InterviewRound(Base):
    __tablename__ = "interview_rounds"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    experience_id = Column(UUID(as_uuid=True), ForeignKey("interview_experiences.id"), nullable=False, index=True)
    round_type = Column(String, nullable=False)
    round_order = Column(Integer, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
