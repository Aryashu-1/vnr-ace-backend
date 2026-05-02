# agents/placements/chart_generator/schemas.py

from typing import Dict, Any, Optional
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


class ChartSpecOutput(BaseModel):
    chart_type: str
    metric: str
    dimension: str
    filters: Dict[str, Any] = Field(default_factory=dict)
    title: str