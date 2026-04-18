from sqlalchemy import Column, DateTime, ForeignKey, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    round_id = Column(UUID(as_uuid=True), ForeignKey("interview_rounds.id"), nullable=False, index=True)
    question_text = Column(Text, nullable=False)
    topic = Column(String, nullable=True, index=True)
    difficulty = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
