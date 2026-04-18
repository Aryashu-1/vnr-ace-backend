from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class PlacementOfferV2(Base):
    __tablename__ = "placement_offers"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    drive_id = Column(UUID(as_uuid=True), ForeignKey("placement_drives.id"), nullable=False, index=True)
    offered_ctc = Column(Float, nullable=True)
    accepted = Column(Boolean, nullable=True, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
