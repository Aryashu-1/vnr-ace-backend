from langgraph.graph import StateGraph, START, END
from typing import Any
from .state import InterviewPrepState
from .nodes import initializer_node, filter_node, answer_node

def build_interview_prep_graph(llm_service: Any, audit_repo: Any = None):
    """
    Builds the LangGraph for the Interview Prep Agent.
    """
    workflow = StateGraph(InterviewPrepState)

    # Add Nodes
    workflow.add_node("initializer", initializer_node)
    workflow.add_node("filter", filter_node)
    workflow.add_node("answer", lambda state: answer_node(state, llm_service))

    # Add Edges
    workflow.add_edge(START, "initializer")
    workflow.add_edge("initializer", "filter")
    workflow.add_edge("filter", "answer")
    workflow.add_edge("answer", END)

    return workflow.compile()
