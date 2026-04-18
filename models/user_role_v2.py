from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.sql import func

from core.db import Base


class UserRoleV2(Base):
    __tablename__ = "user_roles"

    id = Column(String, primary_key=True, index=True)
    profile_id = Column(String, ForeignKey("profiles.id"), nullable=False, index=True)
    role = Column(String, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
