# agents/admissions/graph.py

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.admissions.state import AdmissionsState
from agents.admissions.nodes import (
    public_supervisor_agent, faq_agent, tracking_agent, 
    department_router_agent, admin_agent, create_department_agent
)
from agents.admissions.services import AdmissionsDataService

def compile_admissions_graph():
    """
    Compiles the admissions graph and returns the compiled object.
    """
    departments_data = AdmissionsDataService.load_departments_data()
    
    builder = StateGraph(AdmissionsState)

    builder.add_node("supervisor", public_supervisor_agent)
    builder.add_node("faq", faq_agent)
    builder.add_node("application_tracking", tracking_agent)
    builder.add_node("department_router", department_router_agent)
    builder.add_node("admin_action", admin_agent)

    # Add department nodes dynamically
    for dept_key in departments_data.keys():
        builder.add_node(f"dept_{dept_key}", create_department_agent(dept_key, departments_data))

    # supervisor is entry
    builder.set_entry_point("supervisor")

    # Main routing logic
    builder.add_conditional_edges(
        "supervisor",
        lambda state: state["route"],
        {
            "faq": "faq",
            "application_tracking": "application_tracking",
            "department_query": "department_router",
            "admin_action": "admin_action",
            "direct_response": END,
        },
    )


    # Department routing logic
    dept_routing_map = {key: f"dept_{key}" for key in departments_data.keys()}
    dept_routing_map["not_department"] = END
    dept_routing_map["placements"] = END # Handling placements separately if needed

    builder.add_conditional_edges(
        "department_router",
        lambda state: state.get("dept_route", "not_department"),
        dept_routing_map
    )

    # Terminal nodes
    builder.add_edge("faq", END)
    builder.add_edge("application_tracking", END)
    builder.add_edge("admin_action", END)

    for dept_key in departments_data.keys():
        builder.add_edge(f"dept_{dept_key}", END)

    return builder.compile(checkpointer=MemorySaver())

# Compile the graph instance
admissions_graph = compile_admissions_graph()
