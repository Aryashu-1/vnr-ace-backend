from sqlalchemy import Column, String, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from core.db import Base

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    name = Column(String, nullable=False, index=True, unique=True)
    sector = Column(String, nullable=True)
    domain = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
