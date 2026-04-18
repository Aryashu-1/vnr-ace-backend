from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func

from core.db import Base


class PlacementApplication(Base):
    __tablename__ = "placement_applications"
    __table_args__ = (
        UniqueConstraint("student_id", "drive_id", name="uq_placement_applications_student_drive"),
    )

    id = Column(String, primary_key=True, index=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id"), nullable=False, index=True)
    drive_id = Column(UUID(as_uuid=True), ForeignKey("placement_drives.id"), nullable=False, index=True)
    status = Column(String, nullable=False, default="applied")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
