from typing import TypedDict, List, Dict, Any, Optional

class InterviewPrepState(TypedDict):
    """
    Represents the state of the Interview Prep LangGraph.
    """
    company: str
    topics: List[str]
    company_data: Dict[str, Any]
    filtered_questions: List[Dict[str, Any]]
    user_query: str
    response: Optional[str]
    session_id: str
    audit_events: List[Dict[str, Any]]
