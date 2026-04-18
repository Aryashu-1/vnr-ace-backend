from sqlalchemy import Column, DateTime, ForeignKey, Integer, JSON, String
from sqlalchemy.sql import func

from core.db import Base


class ResumeEmbedding(Base):
    __tablename__ = "resume_embeddings"

    id = Column(String, primary_key=True, index=True)
    resume_id = Column(String, ForeignKey("resumes.id"), nullable=False, index=True)
    embedding = Column(JSON, nullable=True)
    embedding_model = Column(String, nullable=True)
    dimension = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
