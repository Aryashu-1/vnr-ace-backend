# agents/classwork/mail_automation/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from .state import MailAutomationState
from .nodes import *
from functools import partial

def build_mail_graph(llm, email_service, audit_repo, sql_repo):
    g = StateGraph(MailAutomationState)

    g.add_node("access", access_node)
    g.add_node("language", language_node)
    g.add_node("intent", partial(intent_node, llm=llm))
    g.add_node("search", partial(search_node, sql_repo=sql_repo, llm=llm))
    g.add_node("clarification", clarification_node)
    g.add_node("draft", partial(draft_node, llm=llm))
    g.add_node("approval", approval_node)
    g.add_node("decision", decision_node)
    g.add_node("send", partial(send_node, email_service=email_service))
    g.add_node("audit", partial(audit_node, repo=audit_repo))

    g.set_entry_point("access")

    # Entry Routing: If already approved by human, jump to decision
    def route_after_access(s):
        if not s.get("access_granted"):
            return "audit"
        if s.get("human_approved"):
            return "decision"
        return "language"

    g.add_conditional_edges("access", route_after_access)
    
    g.add_conditional_edges("language", lambda s: "intent" if s["safe_language"] else "audit")
    g.add_conditional_edges("intent", lambda s: "clarification" if s["clarification_needed"] else "search")
    g.add_edge("search", "draft")

    g.add_edge("draft", "approval")
    g.add_edge("clarification", "audit")

    # Decision Routing
    g.add_conditional_edges("decision", lambda s: "send" if s["approval_status"] == "approved" else "audit")

    g.add_edge("approval", END)  # Pause point for draft review
    g.add_edge("send", "audit")
    g.add_edge("audit", END)

    return g.compile(checkpointer=MemorySaver())