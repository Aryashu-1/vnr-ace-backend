from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class ChatRequest(BaseModel):
    message: str
    thread_id: Optional[str] = "default_thread"
    metadata: Optional[Dict[str, Any]] = {}

class ChatResponse(BaseModel):
    reply: str
    route: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = {}
    data: Optional[Any] = None
    artifact_path: Optional[str] = None
