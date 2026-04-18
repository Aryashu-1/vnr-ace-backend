from __future__ import annotations

from functools import partial
from typing import Any

from langgraph.graph import END, StateGraph

from .nodes import (
    access_control_node,
    edit_or_generate_node,
    intent_classifier_node,
    language_guardrail_node,
    optional_reanalysis_node,
    response_node,
    section_selector_node,
    validation_node,
    version_save_node,
)
from .state import ResumeEditorState


def build_resume_editor_graph(llm_service: Any = None, editor_service: Any = None, db_factory: Any = None):
    builder = StateGraph(ResumeEditorState)

    builder.add_node("access_control", access_control_node)
    builder.add_node("language_guardrail", language_guardrail_node)
    builder.add_node("intent_classifier", partial(intent_classifier_node, llm_service=llm_service))
    builder.add_node("section_selector", partial(section_selector_node, llm_service=llm_service))
    builder.add_node("edit_or_generate", partial(edit_or_generate_node, editor_service=editor_service))
    builder.add_node("validation", validation_node)
    builder.add_node("version_save", partial(version_save_node, editor_service=editor_service))
    builder.add_node("optional_reanalysis", partial(optional_reanalysis_node, editor_service=editor_service))
    builder.add_node("response", partial(response_node, editor_service=editor_service))

    builder.set_entry_point("access_control")

    def route_after_access(state):
        return "language_guardrail" if state.get("access_granted") else "response"

    def route_after_guardrail(state):
        return "intent_classifier" if state.get("safe_language") else "response"

    def route_after_validation(state):
        return "version_save" if state.get("validation_passed") else "response"

    builder.add_conditional_edges("access_control", route_after_access)
    builder.add_conditional_edges("language_guardrail", route_after_guardrail)
    builder.add_edge("intent_classifier", "section_selector")
    builder.add_edge("section_selector", "edit_or_generate")
    builder.add_edge("edit_or_generate", "validation")
    builder.add_conditional_edges("validation", route_after_validation)
    builder.add_edge("version_save", "optional_reanalysis")
    builder.add_edge("optional_reanalysis", "response")
    builder.add_edge("response", END)

    return builder.compile()
