from datetime import datetime
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

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


class ResumeVersionSummary(BaseModel):
    id: int
    version_number: int
    change_summary: Optional[str] = None
    created_at: Optional[datetime] = None


class ResumeUploadResponse(BaseModel):
    resume_id: str
    structured_json: Dict[str, Any]
    version: ResumeVersionSummary
    analysis: Optional[Dict[str, Any]] = None


class ResumeDetailResponse(BaseModel):
    resume_id: str
    user_id: Optional[str] = None
    current_version_id: Optional[int] = None
    raw_text: Optional[str] = None
    structured_json: Dict[str, Any]
    versions: List[ResumeVersionSummary] = Field(default_factory=list)
    latest_analysis: Optional[Dict[str, Any]] = None
    updated_at: Optional[datetime] = None


class ResumeEditRequest(BaseModel):
    section: Literal["personal_info", "education", "skills", "projects", "experience", "achievements"]
    payload: Any
    subsection_index: Optional[int] = Field(default=None, ge=0)
    change_summary: Optional[str] = None
    reanalyze: bool = False
    user_instruction: Optional[str] = None


class ResumeImproveRequest(BaseModel):
    section: Literal["personal_info", "education", "skills", "projects", "experience", "achievements"]
    action: Literal["improve_section", "regenerate_bullets", "apply_suggestion"] = "improve_section"
    subsection_index: Optional[int] = Field(default=None, ge=0)
    suggestion_text: Optional[str] = None
    user_instruction: Optional[str] = None
    reanalyze: bool = False


class ResumeReanalyzeResponse(BaseModel):
    resume_id: str
    analysis: Dict[str, Any]
    latest_version: Optional[ResumeVersionSummary] = None


class ResumeMutationResponse(BaseModel):
    message: str
    resume_id: str
    structured_json: Dict[str, Any]
    version: Optional[ResumeVersionSummary] = None
    analysis: Optional[Dict[str, Any]] = None

class JobDetailResponse(BaseModel):
    id: str
    role: Optional[str] = None
    ctc: Optional[float] = None
    company_name: str
    external_registration_url: Optional[str] = None
    requires_external_registration: bool = False
    is_registered_externally: bool = False
    status: Optional[str] = "not_applied"
    location: Optional[str] = None
    deadline: Optional[str] = None
    tags: List[str] = []
    description: Optional[str] = None
    criteria: Optional[Dict[str, Any]] = None
    skills: List[str] = []
    examRounds: List[Dict[str, Any]] = []
    instructions: List[str] = []
    experiences: List[Dict[str, Any]] = []

class ExternalRegistrationVerifyRequest(BaseModel):
    external_registration_id: Optional[str] = None
    confirmation_screenshot_url: Optional[str] = None

class PolicyCategory(BaseModel):
    category: str
    items: List[str]

class PolicyResponse(BaseModel):
    policies: List[PolicyCategory]
    last_updated: datetime
