from pydantic import BaseModel
from typing import List, Optional

class Recommendation(BaseModel):
    topic: str
    detail: str
    icon: str

class ProfilePlacementStatsResponse(BaseModel):
    total_applications: int
    rejections: int
    status: str
    recommendations: List[Recommendation]
