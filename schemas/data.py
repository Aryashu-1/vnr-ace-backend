from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime

class StudentBase(BaseModel):
    roll_no: str
    full_name: Optional[str] = None
    gender: Optional[str] = None
    branch: Optional[str] = None
    cgpa: Optional[float] = None
    minor_degree: Optional[str] = None
    intern_status: Optional[bool] = False

class StudentResponse(StudentBase):
    id: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class CompanyBase(BaseModel):
    name: str
    sector: Optional[str] = None

class CompanyResponse(CompanyBase):
    id: str

    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    total: int
    page: int
    size: int
    items: List[Any]
