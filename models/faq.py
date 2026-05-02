from sqlalchemy import Column, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from core.db import Base

class FAQ(Base):
    __tablename__ = "faqs"

    id = Column(UUID(as_uuid=True), primary_key=True, index=True, server_default=text("gen_random_uuid()"))
    question = Column(String, nullable=False)
    answer = Column(Text, nullable=False)
    category = Column(String, nullable=False, index=True)
