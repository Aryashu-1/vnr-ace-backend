# agents/classwork/report_generation/graph.py

from __future__ import annotations

from typing import Any, Callable, Dict

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import ReportGenerationState
from .nodes import (
    access_control_node,
    scope_classifier_node,
    language_guardrail_node,
    planner_node,
    clarification_node,
    load_data_node,
    strict_column_validation_node,
    analysis_node,
    validation_node,
    approval_pause_node,
    human_decision_node,
    final_generation_node,
    followup_node,
    persist_audit_logs_node,
)


def build_report_generation_graph(llm_service: Any = None, audit_repo: Any = None, data_repo: Any = None):
    builder = StateGraph(ReportGenerationState)

    builder.add_node("access_control", access_control_node)
    builder.add_node(
        "scope_classifier",
        lambda state: scope_classifier_node(state, llm_service=llm_service),
    )
    builder.add_node("language_guardrail", language_guardrail_node)
    builder.add_node(
        "planner",
        lambda state: planner_node(state, llm_service=llm_service),
    )
    builder.add_node("clarification", clarification_node)
    builder.add_node("load_data", lambda state: load_data_node(state, data_repo=data_repo))
    builder.add_node("strict_column_validation", strict_column_validation_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("validation", validation_node)
    builder.add_node("approval_pause", approval_pause_node)
    builder.add_node("human_decision", human_decision_node)
    builder.add_node("final_generation", final_generation_node)
    builder.add_node("followup", followup_node)
    builder.add_node(
        "persist_audit_logs",
        lambda state: persist_audit_logs_node(state, audit_repo=audit_repo),
    )

    builder.set_entry_point("access_control")

    def route_after_access(state):
        return "scope_classifier" if state.get("access_granted") else "persist_audit_logs"

    def route_after_scope(state):
        return "language_guardrail" if state.get("in_scope") else "persist_audit_logs"

    def route_after_language(state):
        return "planner" if state.get("safe_language") else "persist_audit_logs"

    def route_after_planner(state):
        return "clarification" if state.get("clarification_needed") else "load_data"

    def route_after_strict_validation(state):
        if state.get("validation_issues"):
            return "validation"
        return "analysis"

    def route_after_validation(state):
        return "approval_pause" if state.get("validation_passed") else "persist_audit_logs"

    def route_after_human_decision(state):
        return "final_generation" if state.get("approval_status") == "approved" else "persist_audit_logs"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("scope_classifier", route_after_scope)
    builder.add_conditional_edges("language_guardrail", route_after_language)
    builder.add_conditional_edges("planner", route_after_planner)

    builder.add_edge("load_data", "strict_column_validation")
    builder.add_conditional_edges("strict_column_validation", route_after_strict_validation)
    builder.add_edge("analysis", "validation")
    builder.add_conditional_edges("validation", route_after_validation)

    # Important:
    # approval_pause is where UI should stop and ask human for approval.
    # Then resume execution by calling the graph again starting from human_decision
    # with state updated to include human_approved.
    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_conditional_edges("human_decision", route_after_human_decision)
    builder.add_edge("final_generation", "followup")
    builder.add_edge("followup", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile(checkpointer=MemorySaver())
