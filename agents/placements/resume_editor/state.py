from typing import Any, Dict, List, Optional, TypedDict


class ResumeEditorState(TypedDict, total=False):
    user_id: str
    user_role: str
    user_query: str
    db_session: Any
    requested_action: Optional[str]
    resume_id: Optional[str]
    section: Optional[str]
    subsection_index: Optional[int]
    payload: Any
    suggestion_text: Optional[str]
    reanalyze: bool

    access_granted: bool
    safe_language: bool
    exploit_detected: bool
    rejection_reason: Optional[str]

    intent: Optional[str]
    intent_confidence: Optional[float]
    selected_section: Optional[str]
    validation_passed: bool
    validation_issues: List[str]

    resume_record: Dict[str, Any]
    current_content: Dict[str, Any]
    updated_content: Dict[str, Any]
    saved_version: Dict[str, Any]
    reanalysis_result: Dict[str, Any]
    resume_versions: List[Dict[str, Any]]

    final_response: Optional[str]
    response_payload: Dict[str, Any]
    audit_events: List[Dict[str, Any]]
