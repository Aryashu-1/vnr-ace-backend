from sqlalchemy import Boolean, Column, Date, DateTime, Float, ForeignKey, String, JSON, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class PlacementDrive(Base):
    __tablename__ = "placement_drives"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)
    role = Column(String, nullable=False)
    ctc = Column(Float, nullable=True)
    drive_date = Column(Date, nullable=True, index=True)
    deadline = Column(Date, nullable=True)
    status = Column(String, nullable=True, default="open")
    criteria = Column(JSON, nullable=True)
    external_registration_url = Column(String, nullable=True)
    requires_external_registration = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
