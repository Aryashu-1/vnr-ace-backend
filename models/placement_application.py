from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
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
    is_registered_externally = Column(Boolean, nullable=False, server_default=text("false"), default=False)
    external_registration_id = Column(String, nullable=True)
    confirmation_screenshot_url = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
