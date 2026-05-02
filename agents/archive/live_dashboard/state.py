# agents/placements/live_dashboard/state.py

from typing import TypedDict, Optional, List, Dict, Any


class LiveDashboardState(TypedDict, total=False):
    # identity
    user_id: str
    user_name: str
    user_role: str

    # conversation
    conversation_id: str
    user_query: str
    messages: List[Dict[str, str]]
    memory: List[Dict[str, Any]]

    # guardrails
    access_granted: bool
    safe_language: bool
    exploit_detected: bool
    in_scope: bool
    rejection_reason: Optional[str]

    # intent
    intent: Optional[str]
    intent_confidence: Optional[float]
    clarification_needed: bool
    clarification_question: Optional[str]

    # dashboard data
    dashboard_loaded: bool
    kpis: Dict[str, Any]
    charts: Dict[str, Any]
    dashboard_snapshot: Dict[str, Any]
    last_refreshed_at: Optional[str]

    # response
    final_response: Optional[str]

    # logs
    audit_events: List[Dict[str, Any]]