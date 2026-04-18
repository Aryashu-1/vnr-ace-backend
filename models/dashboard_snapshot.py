from sqlalchemy import Column, DateTime, Float, Integer, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class DashboardSnapshot(Base):
    __tablename__ = "dashboard_snapshot"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    total_students = Column(Integer, nullable=False, default=0)
    placed_students = Column(Integer, nullable=False, default=0)
    placement_rate = Column(Float, nullable=False, default=0.0)
    avg_package = Column(Float, nullable=False, default=0.0)
    data = Column(JSON, nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
