from pydantic import BaseModel
from typing import List, Optional, Union

class ChartDataPoint(BaseModel):
    name: str # e.g. "2024", "CSE", "< 5 LPA"
    value: Union[int, float]
    total: Optional[int] = None # For branch-wise
    percentage: Optional[float] = None # For branch-wise

class PlacementTrendResponse(BaseModel):
    data: List[ChartDataPoint]

class BranchWiseResponse(BaseModel):
    data: List[ChartDataPoint]

class SalaryDistributionResponse(BaseModel):
    data: List[ChartDataPoint]

class TopHiringResponse(BaseModel):
    data: List[ChartDataPoint]

class MinorImpactResponse(BaseModel):
    data: List[ChartDataPoint]

class MultipleOffersResponse(BaseModel):
    data: List[ChartDataPoint]
