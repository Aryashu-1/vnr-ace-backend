# agents/placements/live_dashboard/graph.py

from __future__ import annotations

from typing import Any
from functools import partial
from langgraph.graph import StateGraph, END

from .state import LiveDashboardState
from .nodes import (
    access_control_node,
    language_guardrail_node,
    scope_classifier_node,
    intent_classifier_node,
    clarification_node,
    load_dashboard_node,
    refresh_dashboard_node,
    dashboard_qa_node,
    memory_update_node,
    persist_audit_logs_node,
)


def build_live_dashboard_graph(
    llm_service: Any = None,
    dashboard_repo: Any = None,
    audit_repo: Any = None,
):
    builder = StateGraph(LiveDashboardState)

    builder.add_node("access_control", access_control_node)
    builder.add_node("language_guardrail", language_guardrail_node)
    builder.add_node(
        "scope_classifier",
        lambda state: scope_classifier_node(state, llm_service=llm_service),
    )
    builder.add_node(
        "intent_classifier",
        lambda state: intent_classifier_node(state, llm_service=llm_service),
    )
    builder.add_node("clarification", clarification_node)
    builder.add_node(
        "load_dashboard",
        partial(load_dashboard_node, dashboard_repo=dashboard_repo),
    )
    builder.add_node(
        "refresh_dashboard",
        partial(refresh_dashboard_node, dashboard_repo=dashboard_repo),
    )
    builder.add_node(
        "dashboard_qa",
        lambda state: dashboard_qa_node(state, llm_service=llm_service),
    )
    builder.add_node("memory_update", memory_update_node)
    builder.add_node(
        "persist_audit_logs",
        lambda state: persist_audit_logs_node(state, audit_repo=audit_repo),
    )

    builder.set_entry_point("access_control")

    def route_after_access(state):
        return "language_guardrail" if state.get("access_granted") else "persist_audit_logs"

    def route_after_language(state):
        return "scope_classifier" if state.get("safe_language") else "persist_audit_logs"

    def route_after_scope(state):
        return "intent_classifier" if state.get("in_scope") else "persist_audit_logs"

    def route_after_intent(state):
        if state.get("clarification_needed"):
            return "clarification"
        if state.get("intent") == "load_dashboard":
            return "load_dashboard"
        if state.get("intent") == "refresh_dashboard":
            return "refresh_dashboard"
        return "dashboard_qa"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("language_guardrail", route_after_language)
    builder.add_conditional_edges("scope_classifier", route_after_scope)
    builder.add_conditional_edges("intent_classifier", route_after_intent)

    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_edge("load_dashboard", "memory_update")
    builder.add_edge("refresh_dashboard", "memory_update")
    builder.add_edge("dashboard_qa", "memory_update")
    builder.add_edge("memory_update", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile()
