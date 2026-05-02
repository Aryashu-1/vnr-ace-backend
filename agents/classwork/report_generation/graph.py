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

    async def _access_control_node(state):
        return await access_control_node(state, data_repo=data_repo)
    builder.add_node("access_control", _access_control_node)

    async def _scope_classifier_node(state):
        return await scope_classifier_node(state, llm_service=llm_service)
    builder.add_node("scope_classifier", _scope_classifier_node)

    builder.add_node("language_guardrail", language_guardrail_node)

    async def _planner_node(state):
        return await planner_node(state, llm_service=llm_service)
    builder.add_node("planner", _planner_node)
    builder.add_node("clarification", clarification_node)
    
    async def _load_data_node(state):
        return await load_data_node(state, data_repo=data_repo)
    builder.add_node("load_data", _load_data_node)
    
    builder.add_node("strict_column_validation", strict_column_validation_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("validation", validation_node)
    builder.add_node("approval_pause", approval_pause_node)
    builder.add_node("human_decision", human_decision_node)
    builder.add_node("final_generation", final_generation_node)
    builder.add_node("followup", followup_node)
    
    async def _persist_audit_logs_node(state):
        return await persist_audit_logs_node(state, audit_repo=audit_repo)
    builder.add_node("persist_audit_logs", _persist_audit_logs_node)

    builder.set_entry_point("access_control")

    def route_after_access(state):
        if not state.get("access_granted"):
            return "persist_audit_logs"
        if state.get("human_approved") is not None:
            return "human_decision"
        return "scope_classifier"

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

    # builder.add_edge("approval_pause", "human_decision") # Removed to allow HITL pause
    
    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_conditional_edges("human_decision", route_after_human_decision)
    builder.add_edge("final_generation", "followup")
    builder.add_edge("followup", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile(checkpointer=MemorySaver())
