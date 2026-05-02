# agents/classwork/report_generation/state.py

from typing import TypedDict, Optional, List, Dict, Any


class ReportGenerationState(TypedDict, total=False):
    # identity / auth
    user_id: str
    user_name: str
    user_role: str
    user_department_id: Optional[str]
    user_department_name: Optional[str]

    # chat context
    user_query: str
    messages: List[Dict[str, str]]
    conversation_id: str
    stop_requested: bool
    followup_mode: bool

    # guardrails / classification
    access_granted: bool
    in_scope: bool
    safe_language: bool
    exploit_detected: bool
    rejection_reason: Optional[str]
    scope_confidence: Optional[float]
    scope_classifier_label: Optional[str]

    # clarification
    clarification_needed: bool
    clarification_question: Optional[str]
    clarification_answer: Optional[str]

    # planner output
    interpreted_intent: Optional[str]
    report_type: Optional[str]
    target_filters: Dict[str, Any]
    required_datasets: List[str]
    export_format: Optional[str]
    plan: Dict[str, Any]

    # data
    loaded_data: Dict[str, Any]
    filtered_df_cache: Dict[str, Any]
    analysis_result: Dict[str, Any]
    preview_result: Dict[str, Any]
    final_dataframe: Any

    # validation
    requested_columns: List[str]
    invalid_filter_columns: List[str]
    validation_passed: bool
    validation_issues: List[str]

    # approval / HITL
    approval_required: bool
    approval_status: Optional[str]   # pending / approved / rejected
    human_approved: Optional[bool]
    approval_notes: Optional[str]
    waiting_for_human: bool

    # final response
    final_response: Optional[str]
    downloadable_artifact_path: Optional[str]

    # logging / persistence
    audit_events: List[Dict[str, Any]]