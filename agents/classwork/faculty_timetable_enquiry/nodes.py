# agents/classwork/faculty_timetable_enquiry/nodes.py

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict

from .constants import (
    AGENT_NAME,
    ALLOWED_INTENTS,
    DB_SCHEMA_HINT,
    SQL_FORBIDDEN_PATTERNS,
    STANDARD_MESSAGES,
)
from .guardrails import check_access, check_language_and_exploit
from .prompts import (
    SCOPE_CLASSIFIER_PROMPT,
    INTENT_CLASSIFIER_PROMPT,
    SQL_GENERATOR_PROMPT,
    ANSWER_FORMATTER_PROMPT,
)
from .schemas import ScopeClassifierOutput, IntentClassifierOutput, SQLGeneratorOutput
from .utils import make_audit_event, compact_rows, trim_memory


def _heuristic_scope(query: str) -> ScopeClassifierOutput:
    q = (query or "").lower()
    kws = ["faculty", "timetable", "schedule", "room", "venue", "section", "period", "cabin", "where"]
    label = "in_scope" if any(k in q for k in kws) else "out_of_scope"
    return ScopeClassifierOutput(label=label, confidence=0.75, reason="Heuristic fallback")


def _heuristic_intent(query: str) -> IntentClassifierOutput:
    q = (query or "").strip()
    ql = q.lower()

    entities: Dict[str, Any] = {}

    room_match = re.search(r"\b(?:room|rm|class(?:room)?)\s*[:\-]?\s*([a-z0-9\-]+)\b", ql)
    if room_match:
        entities["room_no"] = room_match.group(1).upper()

    faculty_match = re.search(r"\b(dr\.?\s+[a-z]+(?:\s+[a-z]+)?)\b", q, flags=re.IGNORECASE)
    if faculty_match:
        entities["faculty_name"] = faculty_match.group(1).strip()

    if "section" in ql:
        entities["section"] = q

    if "subject" in ql:
        entities["subject"] = q

    if "room" in ql or entities.get("room_no"):
        intent = "room_timetable_lookup"
    elif "section" in ql:
        intent = "section_timetable_lookup"
    elif "subject" in ql:
        intent = "subject_timetable_lookup"
    elif any(k in ql for k in ["where", "cabin", "venue"]):
        intent = "faculty_venue_lookup"
    elif any(k in ql for k in ["available", "free", "busy"]):
        intent = "faculty_availability"
    else:
        intent = "faculty_schedule_lookup"

    return IntentClassifierOutput(
        intent=intent,
        confidence=0.65,
        interpreted_entities=entities,
        clarification_needed=False,
        clarification_question=None,
        is_follow_up=False,
        data_strategy="SEARCH_DB"
    )


def access_control_node(state: Dict[str, Any]) -> Dict[str, Any]:
    allowed, reason = check_access(state.get("user_role", ""))
    state["access_granted"] = allowed

    if not allowed:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["access_denied"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "access_denied",
                state["user_id"],
                AGENT_NAME,
                {"role": state.get("user_role"), "query": state.get("user_query")},
            )
        )
    return state


def language_guardrail_node(state: Dict[str, Any]) -> Dict[str, Any]:
    safe, exploit, reason = check_language_and_exploit(state.get("user_query", ""))
    state["safe_language"] = safe
    state["exploit_detected"] = exploit

    if not safe:
        state["rejection_reason"] = reason
        state["final_response"] = STANDARD_MESSAGES["unsafe_language"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "unsafe_or_exploit_query",
                state["user_id"],
                AGENT_NAME,
                {"query": state.get("user_query"), "reason": reason},
            )
        )
    return state


async def scope_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    query = state.get("user_query", "")
    if llm_service is None:
        result = _heuristic_scope(query)
    else:
        try:
            result = await llm_service.ainvoke_structured(
                system_prompt=SCOPE_CLASSIFIER_PROMPT,
                user_prompt=query,
                schema=ScopeClassifierOutput,
            )
        except Exception:
            result = _heuristic_scope(query)

    state["in_scope"] = result.label == "in_scope"

    if not state["in_scope"]:
        state["rejection_reason"] = "out_of_scope"
        state["final_response"] = STANDARD_MESSAGES["out_of_scope"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "out_of_scope_query",
                state["user_id"],
                AGENT_NAME,
                {"query": query, "reason": result.reason, "confidence": result.confidence},
            )
        )
    return state


async def intent_classifier_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    memory = trim_memory(state.get("memory", []), 10)
    user_prompt = (
        f"Conversation memory: {memory}\n"
        f"Current user query: {state.get('user_query', '')}\n"
        f"Allowed intents: {sorted(ALLOWED_INTENTS)}"
    )

    if llm_service is None:
        result = _heuristic_intent(state.get("user_query", ""))
    else:
        try:
            result = await llm_service.ainvoke_structured(
                system_prompt=INTENT_CLASSIFIER_PROMPT,
                user_prompt=user_prompt,
                schema=IntentClassifierOutput,
            )
        except Exception:
            result = _heuristic_intent(state.get("user_query", ""))

    state["intent"] = result.intent
    state["intent_confidence"] = result.confidence
    state["interpreted_entities"] = result.interpreted_entities
    state["clarification_needed"] = result.clarification_needed
    state["clarification_question"] = result.clarification_question
    state["data_strategy"] = result.data_strategy

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "intent_classified",
            state["user_id"],
            AGENT_NAME,
            {
                "intent": result.intent,
                "confidence": result.confidence,
                "entities": result.interpreted_entities,
                "clarification_needed": result.clarification_needed,
                "data_strategy": result.data_strategy,
            },
        )
    )
    return state


def clarification_node(state: Dict[str, Any]) -> Dict[str, Any]:
    state["final_response"] = (
        f"{STANDARD_MESSAGES['clarification_prefix']}\n"
        f"{state.get('clarification_question')}"
    )
    return state


async def faculty_data_loader_node(state: Dict[str, Any], sql_repo: Any = None) -> Dict[str, Any]:
    """
    Loads faculty directory data from the database, with JSON fallback only if needed.
    """
    # Cache optimization: Skip DB if data strategy is REUSE_DATA
    if state.get("data_strategy") == "REUSE_DATA" and state.get("query_result_rows"):
        return state

    if sql_repo is not None:
        try:
            state["query_result_rows"] = await sql_repo.load_faculty_directory(
                interpreted_entities=state.get("interpreted_entities", {}),
                intent=state.get("intent"),
                user_query=state.get("user_query", ""),
            )
            return state
        except Exception as e:
            print(f"Error loading faculty data from DB: {e}")

    # Simplified fallback: in a real system, we might log an error here
    return state


async def sql_generation_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    if llm_service is None:
        raise ValueError("sql_generation_node requires llm_service for production use.")

    SCHEMA_INFO = (
        "Table 'profiles' (p) -> id, full_name\n"
        "Table 'faculty' (f) -> id, profile_id, department, cabin, designation\n"
        "Table 'faculty_schedule_entries' (s) -> faculty_id, day, time_range, activity"
    )

    user_prompt = (
        f"Intent: {state.get('intent')}\n"
        f"Entities: {state.get('interpreted_entities', {})}\n"
        f"Schema: {SCHEMA_INFO}\n"
        f"Current query: {state.get('user_query', '')}\n"
        f"Conversation memory: {trim_memory(state.get('memory', []), 10)}"
    )

    result: SQLGeneratorOutput = await llm_service.ainvoke_structured(
        system_prompt=SQL_GENERATOR_PROMPT,
        user_prompt=user_prompt,
        schema=SQLGeneratorOutput,
    )

    state["sql_query"] = result.sql_query.strip()
    state["sql_params"] = result.sql_params or {}

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "sql_generated",
            state["user_id"],
            AGENT_NAME,
            {"intent": state.get("intent"), "sql": state["sql_query"]},
        )
    )
    return state


def sql_safety_validation_node(state: Dict[str, Any]) -> Dict[str, Any]:
    sql = (state.get("sql_query") or "").strip().lower()
    issues = []

    if not sql.startswith("select"):
        issues.append("Only SELECT queries are allowed.")

    for pattern in SQL_FORBIDDEN_PATTERNS:
        if pattern in sql:
            issues.append(f"Forbidden SQL pattern detected: {pattern}")

    state["sql_validation_issues"] = issues
    state["sql_safe"] = len(issues) == 0

    if not state["sql_safe"]:
        state["final_response"] = STANDARD_MESSAGES["sql_blocked"]
        state.setdefault("audit_events", []).append(
            make_audit_event(
                "sql_blocked",
                state["user_id"],
                AGENT_NAME,
                {"issues": issues, "sql": state.get("sql_query")},
            )
        )
    return state


async def sql_execution_node(state: Dict[str, Any], sql_repo: Any = None) -> Dict[str, Any]:
    if sql_repo is None:
        raise ValueError("sql_execution_node requires sql_repo for production use.")

    rows = await sql_repo.execute_read_only(
        sql_query=state.get("sql_query", ""),
        sql_params=state.get("sql_params", {}),
    )

    state["query_result_rows"] = rows
    state["result_count"] = len(rows)

    state.setdefault("audit_events", []).append(
        make_audit_event(
            "sql_executed",
            state["user_id"],
            AGENT_NAME,
            {"result_count": len(rows)},
        )
    )
    return state


async def answer_formatter_node(state: Dict[str, Any], llm_service: Any = None) -> Dict[str, Any]:
    rows = state.get("query_result_rows", [])

    if not rows:
        state["final_response"] = STANDARD_MESSAGES["no_results"]
        return state

    if llm_service is None:
        state["final_response"] = f"Found data for {len(rows)} matching entries."
        return state

    # Direct JSON-to-Answer flow
    import uuid
    def uuid_serializer(obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable")

    user_prompt = (
        f"User query: {state.get('user_query')}\n"
        f"Extracted Entities: {state.get('interpreted_entities', {})}\n"
        f"Conversation history: {state.get('memory', [])}\n"
        f"Faculty Data (JSON): {json.dumps(rows, indent=2, default=uuid_serializer)}\n"
    )
    
    system_prompt = (
        "You are a helpful Faculty Enquiry assistant. "
        "Answer the user's query strictly based on the provided Faculty Data JSON, while considering the conversation history. "
        "Include cabin numbers, designations, and schedules in your answer where relevant. "
        "If a specific faculty is found, give their full details. "
        "If multiple matches or no matches, explain why clearly."
    )
    
    try:
        answer = await llm_service.ainvoke_text(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        state["final_response"] = answer
    except Exception:
        # Fallback response
        state["final_response"] = (
            f"Found {len(rows)} matching record(s). "
            f"Here are key details: {compact_rows(rows, limit=3)}"
        )
    return state


def memory_update_node(state: Dict[str, Any]) -> Dict[str, Any]:
    memory = state.get("memory", [])
    memory.append({
        "user_query": state.get("user_query"),
        "intent": state.get("intent"),
        "entities": state.get("interpreted_entities", {}),
        "sql_query": state.get("sql_query"),
        "result_count": state.get("result_count", 0),
    })
    state["memory"] = trim_memory(memory, 20)
    return state


async def persist_audit_logs_node(state: Dict[str, Any], audit_repo: Any = None) -> Dict[str, Any]:
    if audit_repo is not None:
        await audit_repo.persist_events(state.get("audit_events", []))
    return state
