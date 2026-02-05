from typing import TypedDict, Optional, Literal
from langgraph.graph import StateGraph, END
from core.llm import call_llm

# ---------------------------
#   State Definition
# ---------------------------

class PlacementsState(TypedDict):
    user_id: Optional[int]
    role: Optional[str]  # e.g., 'student', 'admin', 'coordinator'
    message: str
    intent: Optional[str]
    authorized: bool
    response: Optional[str]
    validation_status: Optional[str] # 'approved', 'rejected'

# ---------------------------
#   GENERIC NODES (Reusable)
# ---------------------------

async def rbac_node(state: PlacementsState):
    """
    Checks authorization. 
    NOTE: Bypassed for testing as per request.
    """
    return {"authorized": True}

async def validator_node(state: PlacementsState):
    """
    Validates the generated response.
    """
    response = state.get("response")
    if response and "error" not in response.lower():
        return {"validation_status": "approved"}
    return {"validation_status": "rejected"}

# ---------------------------
#   DASHBOARD GRAPH
# ---------------------------

async def dashboard_agent(state: PlacementsState):
    # Simulated logic
    return {"response": "Here is your Placement Dashboard: \n- Eligible: 5 Companies\n- Applied: 2\n- Status: In Progress"}

dashboard_builder = StateGraph(PlacementsState)
dashboard_builder.add_node("rbac", rbac_node)
dashboard_builder.add_node("dashboard_agent", dashboard_agent)
dashboard_builder.add_node("validator", validator_node)

dashboard_builder.set_entry_point("rbac")
dashboard_builder.add_edge("rbac", "dashboard_agent")
dashboard_builder.add_edge("dashboard_agent", "validator")
dashboard_builder.add_edge("validator", END)

dashboard_graph = dashboard_builder.compile()

# ---------------------------
#   RESUME GRAPH
# ---------------------------

async def resume_agent(state: PlacementsState):
    prompt = f"Analyze this resume request: {state['message']}. Return a constructive critique."
    # response = await call_llm(prompt) 
    response = "Resume Analysis: formatting looks good, add more metrics to your projects." # Mock for speed
    return {"response": response}

resume_builder = StateGraph(PlacementsState)
resume_builder.add_node("rbac", rbac_node)
resume_builder.add_node("resume_agent", resume_agent)
resume_builder.add_node("validator", validator_node)

resume_builder.set_entry_point("rbac")
resume_builder.add_edge("rbac", "resume_agent")
resume_builder.add_edge("resume_agent", "validator")
resume_builder.add_edge("validator", END)

resume_graph = resume_builder.compile()

# ---------------------------
#   PREP GRAPH
# ---------------------------

async def prep_agent(state: PlacementsState):
    return {"response": "Here are some study materials for your upcoming interview."}

prep_builder = StateGraph(PlacementsState)
prep_builder.add_node("rbac", rbac_node)
prep_builder.add_node("prep_agent", prep_agent)
prep_builder.add_node("validator", validator_node)

prep_builder.set_entry_point("rbac")
prep_builder.add_edge("rbac", "prep_agent")
prep_builder.add_edge("prep_agent", "validator")
prep_builder.add_edge("validator", END)

prep_graph = prep_builder.compile()

# ---------------------------
#   SHORTLISTING GRAPH
# ---------------------------

async def shortlisting_agent(state: PlacementsState):
    return {"response": "You have been shortlisted for: \n- TechCorp Inc.\n- Global Solutions"}

shortlisting_builder = StateGraph(PlacementsState)
shortlisting_builder.add_node("rbac", rbac_node)
shortlisting_builder.add_node("shortlisting_agent", shortlisting_agent)
shortlisting_builder.add_node("validator", validator_node)

shortlisting_builder.set_entry_point("rbac")
shortlisting_builder.add_edge("rbac", "shortlisting_agent")
shortlisting_builder.add_edge("shortlisting_agent", "validator")
shortlisting_builder.add_edge("validator", END)

shortlisting_graph = shortlisting_builder.compile()

# ---------------------------
#   TRACKING GRAPH
# ---------------------------

async def tracking_agent(state: PlacementsState):
    return {"response": "Tracking Update: Your application to Cloud Systems is 'Under Review'."}

tracking_builder = StateGraph(PlacementsState)
tracking_builder.add_node("rbac", rbac_node)
tracking_builder.add_node("tracking_agent", tracking_agent)
tracking_builder.add_node("validator", validator_node)

tracking_builder.set_entry_point("rbac")
tracking_builder.add_edge("rbac", "tracking_agent")
tracking_builder.add_edge("tracking_agent", "validator")
tracking_builder.add_edge("validator", END)

tracking_graph = tracking_builder.compile()

# ---------------------------
#   NOTIFICATION GRAPH
# ---------------------------

async def notification_agent(state: PlacementsState):
    return {"response": "No new notifications at this time."}

notification_builder = StateGraph(PlacementsState)
notification_builder.add_node("rbac", rbac_node)
notification_builder.add_node("notification_agent", notification_agent)
notification_builder.add_node("validator", validator_node)

notification_builder.set_entry_point("rbac")
notification_builder.add_edge("rbac", "notification_agent")
notification_builder.add_edge("notification_agent", "validator")
notification_builder.add_edge("validator", END)

notification_graph = notification_builder.compile()
