# langgraph/admissions_graph.py

from langgraph.graph import StateGraph, END

from langgraph.prebuilt import ToolNode
from typing import TypedDict, Optional

from core.llm import call_llm

# ---------------------------
#   State Definition
# ---------------------------

class AdmissionsState(TypedDict):
    message: str
    reply: Optional[str]
    route: Optional[str]  # which agent the supervisor selected


# ---------------------------
#   AGENTS
# ---------------------------

async def public_supervisor_agent(state: AdmissionsState):
    """
    This supervisor decides which agent should handle the message.
    """

    prompt = f"""
    You are the PUBLIC SUPERVISOR AGENT for VNR-ACE Admissions.

    Classify the following user message into EXACTLY one route:
    - faq
    - application_tracking
    - department_query
    - admin_action  (only if explicitly admin activity)
    - unknown

    User message: {state['message']}

    Return ONLY the route name.
    """

    route = (await call_llm(prompt)).strip().lower()

    # ensure normalization
    if route not in ["faq", "application_tracking", "department_query", "admin_action"]:
        route = "faq"

    return {"route": route}


# -----------------------
# FAQ AGENT
# -----------------------

async def faq_agent(state: AdmissionsState):
    prompt = f"""
    You are the VNR-ACE Admissions FAQ Agent.
    Answer clearly and concisely.

    Student question:
    {state['message']}
    """

    answer = await call_llm(prompt)
    return {"reply": answer}


# -----------------------
# APPLICATION TRACKING AGENT
# -----------------------

async def tracking_agent(state: AdmissionsState):
    prompt = f"""
    You are the Application Tracking Agent for VNR-ACE.

    The user is asking about application status.

    Provide a helpful response.
    """

    answer = await call_llm(prompt)
    return {"reply": answer}


# -----------------------
# DEPARTMENT ROUTER AGENT
# -----------------------

async def department_router_agent(state: AdmissionsState):
    prompt = f"""
    You are the DEPARTMENT ROUTING AGENT for VNR-ACE.

    User query:
    {state['message']}

    Determine which department this message belongs to:
    - cse
    - it
    - ece
    - eee
    - mechanical
    - civil
    - not_department

    Return ONLY the department key.
    """

    dept = (await call_llm(prompt)).strip().lower()
    return {"reply": f"This will be routed to department: {dept}"}


# -----------------------
# ADMIN ACTION AGENT
# -----------------------

async def admin_agent(state: AdmissionsState):
    prompt = f"""
    You are the ADMIN SUPPORT AGENT for VNR-ACE Admissions.
    You ONLY assist administrators in performing tasks related to applications.

    Admin message:
    {state['message']}

    Provide a structured, useful response.
    """

    answer = await call_llm(prompt)
    return {"reply": answer}


# ---------------------------
# GRAPH DEFINITION
# ---------------------------

graph = StateGraph(AdmissionsState)

graph.add_node("supervisor", public_supervisor_agent)
graph.add_node("faq", faq_agent)
graph.add_node("application_tracking", tracking_agent)
graph.add_node("department_query", department_router_agent)
graph.add_node("admin_action", admin_agent)

# supervisor is entry
graph.set_entry_point("supervisor")

# routing logic
graph.add_conditional_edges(
    "supervisor",
    lambda state: state["route"],
    {
        "faq": "faq",
        "application_tracking": "application_tracking",
        "department_query": "department_query",
        "admin_action": "admin_action",
    },
)

# every agent ends the cycle
graph.add_edge("faq", END)
graph.add_edge("application_tracking", END)
graph.add_edge("department_query", END)
graph.add_edge("admin_action", END)

admissions_graph = graph.compile()
