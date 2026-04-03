# agents/classwork/mail_automation/graph.py

from langgraph.graph import StateGraph, END
from .state import MailAutomationState
from .nodes import *


def build_mail_graph(llm, email_service, audit_repo, sql_repo):
    g = StateGraph(MailAutomationState)

    g.add_node("access", access_node)
    g.add_node("language", language_node)
    g.add_node("intent", lambda s: intent_node(s, llm))
    g.add_node("search", lambda s: search_node(s, sql_repo))
    g.add_node("clarification", clarification_node)
    g.add_node("draft", lambda s: draft_node(s, llm))
    g.add_node("approval", approval_node)
    g.add_node("decision", decision_node)
    g.add_node("send", lambda s: send_node(s, email_service))
    g.add_node("audit", lambda s: audit_node(s, audit_repo))

    g.set_entry_point("access")

    g.add_conditional_edges("access", lambda s: "language" if s["access_granted"] else "audit")
    g.add_conditional_edges("language", lambda s: "intent" if s["safe_language"] else "audit")
    g.add_conditional_edges("intent", lambda s: "clarification" if s["clarification_needed"] else "search")
    g.add_edge("search", "draft")

    g.add_edge("draft", "approval")
    g.add_edge("clarification", "audit")

    g.add_conditional_edges("decision", lambda s: "send" if s["approval_status"] == "approved" else "audit")

    g.add_edge("approval", END)  # pause
    g.add_edge("send", "audit")
    g.add_edge("audit", END)

    return g.compile()