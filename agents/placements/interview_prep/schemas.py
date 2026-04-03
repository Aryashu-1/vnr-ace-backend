from pydantic import BaseModel
from typing import List, Optional

class InterviewStartRequest(BaseModel):
    company: str
    topics: List[str]

class InterviewChatRequest(BaseModel):
    session_id: str
    message: str

class FilterSchema(BaseModel):
    relevant_ids: List[str]
    explanation: str

class LLMAnswerSchema(BaseModel):
    explanation: str
    approach: str
    code: Optional[str]
    tips: str
