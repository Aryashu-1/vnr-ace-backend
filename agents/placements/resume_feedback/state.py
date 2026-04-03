# agents/placements/resume_feedback/state.py

from typing import TypedDict, Optional, List, Dict, Any


class ResumeFeedbackState(TypedDict, total=False):
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

    # resume context
    resume_id: Optional[str]
    resume_path: Optional[str]
    resume_text: Optional[str]

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

    # cache / rag
    cached_analysis_found: bool
    cache_key: Optional[str]
    rag_executed: bool

    # outputs
    structured_analysis: Dict[str, Any]
    final_response: Optional[str]

    # multi-turn chat history (Gemini format: [{role, parts}])
    conversation_history: List[Dict[str, Any]]

    # logs
    audit_events: List[Dict[str, Any]]