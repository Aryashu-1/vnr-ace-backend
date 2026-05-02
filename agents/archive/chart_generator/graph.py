# agents/placements/chart_generator/graph.py

from __future__ import annotations

from typing import Any
from langgraph.graph import StateGraph, END

from .state import ChartGeneratorState
from .nodes import (
    access_control_node,
    language_guardrail_node,
    scope_classifier_node,
    intent_classifier_node,
    clarification_node,
    chart_spec_node,
    data_prep_node,
    chart_generation_node,
    chart_explanation_node,
    memory_update_node,
    persist_audit_logs_node,
)


def build_chart_generator_graph(
    llm_service: Any = None,
    analytics_repo: Any = None,
    audit_repo: Any = None,
):
    builder = StateGraph(ChartGeneratorState)

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
        "chart_spec",
        lambda state: chart_spec_node(state, llm_service=llm_service),
    )
    builder.add_node(
        "data_prep",
        lambda state: data_prep_node(state, analytics_repo=analytics_repo),
    )
    builder.add_node("chart_generation", chart_generation_node)
    builder.add_node(
        "chart_explanation",
        lambda state: chart_explanation_node(state, llm_service=llm_service),
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
        if state.get("intent") == "explain_chart":
            return "chart_explanation"
        return "chart_spec"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("language_guardrail", route_after_language)
    builder.add_conditional_edges("scope_classifier", route_after_scope)
    builder.add_conditional_edges("intent_classifier", route_after_intent)

    builder.add_edge("chart_spec", "data_prep")
    builder.add_edge("data_prep", "chart_generation")
    builder.add_edge("chart_generation", "memory_update")
    builder.add_edge("chart_explanation", "memory_update")
    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_edge("memory_update", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile()