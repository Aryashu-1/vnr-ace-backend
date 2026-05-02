# agents/placements/resume_feedback/schemas.py

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field


class ScopeClassifierOutput(BaseModel):
    label: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class IntentClassifierOutput(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None


class ResumeFollowupAnswerOutput(BaseModel):
    answer: str


class SectionFeedback(BaseModel):
    score: float = Field(..., ge=0.0, le=10.0)
    strengths: List[str] = Field(default_factory=list)
    issues: List[str] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)
    example_rewrites: List[str] = Field(default_factory=list)


class StructuredResumeAnalysis(BaseModel):
    overall_score: float = Field(..., ge=0.0, le=100.0)
    summary: List[str] = Field(default_factory=list)
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    ats_issues: List[str] = Field(default_factory=list)
    priority_fixes: List[str] = Field(default_factory=list)
    section_feedback: Dict[str, SectionFeedback] = Field(default_factory=dict)