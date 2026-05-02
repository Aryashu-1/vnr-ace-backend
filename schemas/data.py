from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Any
from datetime import datetime

class StudentBase(BaseModel):
    rollNumber: str = Field(alias="roll_no", serialization_alias="rollNumber")
    name: Optional[str] = Field(None, alias="full_name", serialization_alias="name")
    gender: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    minor_degree: Optional[str] = None
    intern_status: Optional[bool] = False
    placed: bool = False
    company: Optional[str] = None
    salary: Optional[float] = Field(None, alias="highest_package", serialization_alias="salary")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

class StudentResponse(StudentBase):
    id: Any
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CompanyBase(BaseModel):
    name: str
    sector: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: Any

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[Any]
