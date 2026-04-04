from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ResumeAnalysisRequest(BaseModel):
    resume_text: Optional[str] = None
    resume_id: Optional[str] = None

class ShortlistingRequest(BaseModel):
    jd_text: str
    no_of_students: Optional[int] = 5
    min_cgpa: Optional[float] = None
    branch: Optional[str] = None
    company: Optional[str] = None

class InterviewStartRequest(BaseModel):
    company: str
    topics: Optional[List[str]] = []

class InterviewChatRequest(BaseModel):
    session_id: str
    message: str

class PlacementStats(BaseModel):
    label: str
    value: str
    trend: Optional[int] = None

class RecentPlacement(BaseModel):
    name: str
    branch: str
    company: str
    package: str

class DashboardResponse(BaseModel):
    stats: List[PlacementStats]
    recent_placements: List[RecentPlacement]
