# agents/classwork/faculty_timetable_enquiry/state.py

from typing import TypedDict, Optional, List, Dict, Any


class FacultyTimetableEnquiryState(TypedDict, total=False):
    # identity
    user_id: str
    user_name: str
    user_role: str

    # conversation
    conversation_id: str
    user_query: str
    messages: List[Dict[str, str]]
    memory: List[Dict[str, Any]]
    stop_requested: bool

    # guardrails
    access_granted: bool
    safe_language: bool
    exploit_detected: bool
    in_scope: bool
    rejection_reason: Optional[str]

    # understanding
    intent: Optional[str]
    intent_confidence: Optional[float]
    interpreted_entities: Dict[str, Any]
    clarification_needed: bool
    clarification_question: Optional[str]

    # sql
    sql_query: Optional[str]
    sql_params: Dict[str, Any]
    sql_safe: bool
    sql_validation_issues: List[str]

    # retrieval
    data_strategy: Optional[str] # REUSE_DATA, SEARCH_DB, DYNAMIC_SQL
    
    # result
    query_result_rows: List[Dict[str, Any]]
    result_count: int
    final_response: Optional[str]

    # logs
    audit_events: List[Dict[str, Any]]