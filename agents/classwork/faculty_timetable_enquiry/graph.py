# agents/classwork/faculty_timetable_enquiry/graph.py

from __future__ import annotations

from typing import Any
from functools import partial
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import FacultyTimetableEnquiryState
from .nodes import (
    access_control_node,
    language_guardrail_node,
    scope_classifier_node,
    intent_classifier_node,
    clarification_node,
    faculty_data_loader_node,
    answer_formatter_node,
    memory_update_node,
    persist_audit_logs_node,
)


def build_faculty_timetable_enquiry_graph(
    llm_service: Any = None,
    sql_repo: Any = None,
    audit_repo: Any = None,
):
    builder = StateGraph(FacultyTimetableEnquiryState)

    builder.add_node("access_control", access_control_node)
    builder.add_node("language_guardrail", language_guardrail_node)
    builder.add_node(
        "scope_classifier",
        partial(scope_classifier_node, llm_service=llm_service),
    )
    builder.add_node(
        "intent_classifier",
        partial(intent_classifier_node, llm_service=llm_service),
    )
    builder.add_node("clarification", clarification_node)
    builder.add_node(
        "data_loader",
        partial(faculty_data_loader_node, sql_repo=sql_repo),
    )
    builder.add_node(
        "answer_formatter",
        partial(answer_formatter_node, llm_service=llm_service),
    )
    builder.add_node("memory_update", memory_update_node)
    builder.add_node(
        "persist_audit_logs",
        partial(persist_audit_logs_node, audit_repo=audit_repo),
    )

    builder.set_entry_point("access_control")

    def route_after_access(state):
        return "language_guardrail" if state.get("access_granted") else "persist_audit_logs"

    def route_after_language(state):
        return "scope_classifier" if state.get("safe_language") else "persist_audit_logs"

    def route_after_scope(state):
        return "intent_classifier" if state.get("in_scope") else "persist_audit_logs"

    def route_after_intent(state):
        return "clarification" if state.get("clarification_needed") else "data_loader"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("language_guardrail", route_after_language)
    builder.add_conditional_edges("scope_classifier", route_after_scope)
    builder.add_conditional_edges("intent_classifier", route_after_intent)
    builder.add_edge("data_loader", "answer_formatter")
    builder.add_edge("answer_formatter", "memory_update")
    builder.add_edge("memory_update", "persist_audit_logs")
    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile(checkpointer=MemorySaver())
