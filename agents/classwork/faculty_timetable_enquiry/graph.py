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
    sql_generation_node,
    sql_safety_validation_node,
    sql_execution_node,
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

    async def _access_control_node(state):
        return access_control_node(state)
    builder.add_node("access_control", _access_control_node)

    async def _language_guardrail_node(state):
        return language_guardrail_node(state)
    builder.add_node("language_guardrail", _language_guardrail_node)

    async def _scope_classifier_node(state):
        return await scope_classifier_node(state, llm_service=llm_service)
    builder.add_node("scope_classifier", _scope_classifier_node)

    async def _intent_classifier_node(state):
        return await intent_classifier_node(state, llm_service=llm_service)
    builder.add_node("intent_classifier", _intent_classifier_node)

    async def _clarification_node(state):
        return clarification_node(state)
    builder.add_node("clarification", _clarification_node)
    
    # Data Retrieval Strategy Nodes
    async def _data_loader_node(state):
        return await faculty_data_loader_node(state, sql_repo=sql_repo)
    builder.add_node("data_loader", _data_loader_node)

    async def _sql_generation_node(state):
        return await sql_generation_node(state, llm_service=llm_service)
    builder.add_node("sql_generation", _sql_generation_node)

    async def _sql_safety_validation_node(state):
        return sql_safety_validation_node(state)
    builder.add_node("sql_safety_validation", _sql_safety_validation_node)

    async def _sql_execution_node(state):
        return await sql_execution_node(state, sql_repo=sql_repo)
    builder.add_node("sql_execution", _sql_execution_node)
    
    async def _answer_formatter_node(state):
        return await answer_formatter_node(state, llm_service=llm_service)
    builder.add_node("answer_formatter", _answer_formatter_node)

    async def _memory_update_node(state):
        return memory_update_node(state)
    builder.add_node("memory_update", _memory_update_node)

    async def _persist_audit_logs_node(state):
        return await persist_audit_logs_node(state, audit_repo=audit_repo)
    builder.add_node("persist_audit_logs", _persist_audit_logs_node)

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
        
        strategy = state.get("data_strategy", "SEARCH_DB")
        if strategy == "REUSE_DATA":
            return "answer_formatter"
        elif strategy == "DYNAMIC_SQL":
            return "sql_generation"
        else:
            return "data_loader"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("language_guardrail", route_after_language)
    builder.add_conditional_edges("scope_classifier", route_after_scope)
    builder.add_conditional_edges("intent_classifier", route_after_intent)
    
    builder.add_edge("sql_generation", "sql_safety_validation")
    builder.add_conditional_edges(
        "sql_safety_validation",
        lambda state: "sql_execution" if state.get("sql_safe") else "persist_audit_logs"
    )
    builder.add_edge("sql_execution", "answer_formatter")
    builder.add_edge("data_loader", "answer_formatter")
    
    builder.add_edge("answer_formatter", "memory_update")
    builder.add_edge("memory_update", "persist_audit_logs")
    builder.add_edge("clarification", "persist_audit_logs")
    builder.add_edge("persist_audit_logs", END)

    return builder.compile(checkpointer=MemorySaver())
