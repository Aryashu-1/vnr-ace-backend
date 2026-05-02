# agents/placements/chart_generator/state.py

from typing import TypedDict, Optional, List, Dict, Any


class ChartGeneratorState(TypedDict, total=False):
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

    # understanding
    intent: Optional[str]
    intent_confidence: Optional[float]
    clarification_needed: bool
    clarification_question: Optional[str]

    # chart spec
    chart_type: Optional[str]
    metric: Optional[str]
    dimension: Optional[str]
    filters: Dict[str, Any]
    title: Optional[str]

    # chart data + artifact
    chart_dataframe: Any
    chart_rows: List[Dict[str, Any]]
    chart_spec: Dict[str, Any]
    chart_path: Optional[str]

    # response
    final_response: Optional[str]

    # logs
    audit_events: List[Dict[str, Any]]