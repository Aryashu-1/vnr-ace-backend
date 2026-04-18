# agents/placements/live_dashboard/nodes.py

from __future__ import annotations

from typing import Any, Dict

from .constants import AGENT_NAME, ALLOWED_INTENTS, STANDARD_MESSAGES
from .guardrails import check_access, check_language_and_exploit
from .prompts import (
    SCOPE_CLASSIFIER_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    DASHBOARD_QA_PROMPT,
)
from .schemas import ScopeClassifierOutput, IntentClassifierOutput
from .utils import make_audit_event, trim_memory, summarize_charts_for_prompt, utc_now_iso


def access_control_node(state: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_access(state.get("user_role", ""))
    state["access_granted"] = allowed

    if not allowed:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
    return state


def language_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    safe, exploit, reason = check_language_and_exploit(state.get("user_query", ""))
    state["safe_language"] = safe
    state["exploit_detected"] = exploit

    if not safe:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["unsafe_language"]
    return state


def scope_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    query = state.get("user_query", "")

    if llm_service is None:
        q = query.lower()
        kws = ["dashboard", "kpi", "placement", "offers", "package", "refresh"]
        label = "in_scope" if any(k in q for k in kws) else "out_of_scope"
        result = ScopeClassifierOutput(label=label, confidence=0.75, reason="Heuristic fallback")
    else:
        result = llm_service.invoke_structured(
            system_prompt=SCOPE_CLASSIFIER_PROMPT,
            user_prompt=query,
            schema=ScopeClassifierOutput,
        )

    state["in_scope"] = result.label == "in_scope"

    if not state["in_scope"]:
        state["rejection_reason"] = "out_of_scope"
        state["final_response"] = STANDARD_MESSAGES["out_of_scope"]
    return state


def intent_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("intent_classifier_node requires llm_service for production use.")

    user_prompt = (
        f"Conversation memory: {trim_memory(state.get('memory', []), 10)}\n"
        f"Current user query: {state.get('user_query', '')}\n"
        f"Allowed intents: {sorted(ALLOWED_INTENTS)}"
    )

    result: IntentClassifierOutput = llm_service.invoke_structured(
        system_prompt=INTENT_CLASSIFIER_PROMPT,
        user_prompt=user_prompt,
        schema=IntentClassifierOutput,
    )

    state["intent"] = result.intent
    state["intent_confidence"] = result.confidence
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question
    return state


def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state["final_response"] = (
        f"{STANDARD_MESSAGES['clarification_prefix']}\n"
        f"{state.get('clarification_question')}"
    )
    return state


async def load_dashboard_node(state: Dict[str, Any], dashboard_repo: Any = None) -> Dict[str, Any]:
    if dashboard_repo is None:
        snapshot = {
            "kpis": {
                "total_students": 540,
                "eligible_students": 470,
                "placed_students": 312,
                "unplaced_students": 158,
                "placement_rate": 66.38,
                "total_offers": 428,
                "average_package": 7.4,
                "highest_package": 24.0,
                "active_companies": 39,
            },
            "charts": {
                "department_wise_placements": {
                    "title": "Department-wise Placements",
                    "rows": [
                        {"department": "CSE", "placed_students": 140},
                        {"department": "ECE", "placed_students": 82},
                        {"department": "EEE", "placed_students": 40},
                        {"department": "MECH", "placed_students": 50},
                    ],
                },
                "month_wise_offers": {
                    "title": "Month-wise Offers",
                    "rows": [
                        {"month": "Aug", "offers": 30},
                        {"month": "Sep", "offers": 48},
                        {"month": "Oct", "offers": 72},
                        {"month": "Nov", "offers": 96},
                    ],
                },
                "company_wise_hires": {
                    "title": "Company-wise Hires",
                    "rows": [
                        {"company": "Accenture", "students": 52},
                        {"company": "TCS", "students": 46},
                        {"company": "Infosys", "students": 34},
                    ],
                },
            },
        }
    else:
        snapshot = await dashboard_repo.load_dashboard_snapshot()

    state["dashboard_snapshot"] = snapshot
    state["kpis"] = snapshot.get("kpis", {})
    state["charts"] = snapshot.get("charts", {})
    state["dashboard_loaded"] = True
    state["last_refreshed_at"] = utc_now_iso()

    state["final_response"] = (
        f"{STANDARD_MESSAGES['dashboard_loaded']}\n"
        f"KPIs: {state['kpis']}\n"
        f"Charts available: {list(state['charts'].keys())}"
    )
    return state


async def refresh_dashboard_node(state: Dict[str, Any], dashboard_repo: Any = None) -> Dict[str, Any]:
    state = await load_dashboard_node(state, dashboard_repo=dashboard_repo)
    state["final_response"] = (
        f"{STANDARD_MESSAGES['dashboard_refreshed']}\n"
        f"Last refreshed at: {state.get('last_refreshed_at')}\n"
        f"KPIs: {state.get('kpis', {})}"
    )
    return state


def dashboard_qa_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if not state.get("dashboard_loaded"):
        state["final_response"] = STANDARD_MESSAGES["dashboard_not_loaded"]
        return state

    kpis = state.get("kpis", {})
    charts = summarize_charts_for_prompt(state.get("charts", {}))

    if not kpis and not charts:
        state["final_response"] = STANDARD_MESSAGES["no_data"]
        return state

    if llm_service is None:
        state["final_response"] = (
            f"Dashboard answer based on current data.\n"
            f"KPIs: {kpis}\n"
            f"Chart summaries: {charts}"
        )
        return state

    prompt = (
        f"User question: {state.get('user_query')}\n"
        f"Available KPIs: {kpis}\n"
        f"Available chart summaries: {charts}"
    )
    answer = llm_service.invoke_text(
        system_prompt=DASHBOARD_QA_PROMPT,
        user_prompt=prompt,
    )
    state["final_response"] = answer
    return state


def memory_update_node(state: Dict[str, Any]) -> Dict[str, Any]:
    memory = state.get("memory", [])
    memory.append({
        "user_query": state.get("user_query"),
        "intent": state.get("intent"),
        "dashboard_loaded": state.get("dashboard_loaded", False),
        "last_refreshed_at": state.get("last_refreshed_at"),
    })
    state["memory"] = trim_memory(memory, 20)
    return state


def persist_audit_logs_node(state: Dict[str, Any], audit_repo: Any = None) -> Dict[str, Any]:
    if audit_repo is not None:
        audit_repo.persist_events(state.get("audit_events", []))
    return state
