# agents/classwork/faculty_timetable_enquiry/schemas.py

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class ScopeClassifierOutput(BaseModel):
    label: str = Field(..., description="in_scope or out_of_scope")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reason: str


class IntentClassifierOutput(BaseModel):
    intent: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    interpreted_entities: Dict[str, Any] = Field(default_factory=dict)
    clarification_needed: bool = False
    clarification_question: Optional[str] = None
    is_follow_up: bool = False
    data_strategy: str = "SEARCH_DB"


class SQLGeneratorOutput(BaseModel):
    sql_query: str
    sql_params: Dict[str, Any] = Field(default_factory=dict)
    explanation: str