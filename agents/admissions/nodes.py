import re
from typing import Dict, Any, List
from langgraph.graph.message import AnyMessage
from core.llm import call_llm
from agents.admissions.state import AdmissionsState
from agents.admissions.prompts import (
    SUPERVISOR_PROMPT, FAQ_PROMPT, TRACKING_PROMPT, 
    DEPT_ROUTING_PROMPT, ADMIN_PROMPT, DEPT_HEAD_PROMPT
)
from agents.admissions.services import AdmissionsDataService

def format_history(messages: List[AnyMessage]) -> str:
    """Formats the list of messages into a readable string for the prompt."""
    history_str = ""
    for msg in messages[:-1]: # Exclude the very last message which is usually the current query
        role = "User" if msg.type == "human" else "Assistant"
        content = msg.content
        history_str += f"{role}: {content}\n"
    return history_str if history_str else "No previous history."

async def public_supervisor_agent(state: AdmissionsState):
    """
    Decides the next agent to handle the user request.
    """
    departments_data = AdmissionsDataService.load_departments_data()
    dept_list = ", ".join([info['name'] for info in departments_data.values()])
    history = format_history(state.get("messages", []))

    prompt = SUPERVISOR_PROMPT.format(
        dept_list=dept_list, 
        message=state['message'],
        history=history
    )
    response = (await call_llm(prompt)).strip()

    if response.startswith("direct_response:"):
        reply = response.replace("direct_response:", "").strip()
        return {"route": "direct_response", "reply": reply, "messages": [("assistant", reply)]}

    route = response.lower()
    if route not in ["faq", "application_tracking", "department_query", "admin_action"]:
        route = "faq"

    return {"route": route}



async def faq_agent(state: AdmissionsState):
    """
    Handles general admissions FAQs.
    """
    departments_data = AdmissionsDataService.load_departments_data()
    
    # Context for admissions FAQ
    admissions_context = ""
    if "admissions" in departments_data:
        admissions_context = departments_data['admissions']['content']
    
    # Summary of all departments for comparison
    dept_summaries = []
    for d_key, d_info in departments_data.items():
        if d_key != "admissions":
            # Just take the first few lines as summary
            content_lines = d_info['content'].split('\n')[:5]
            summary = " ".join(content_lines)
            dept_summaries.append(f"- {d_info['name']}: {summary}")
    
    dept_context = "\nDepartment Overviews:\n" + "\n".join(dept_summaries)
    
    full_context = f"Admissions Context:\n{admissions_context}\n{dept_context}"

    history = format_history(state.get("messages", []))
    prompt = FAQ_PROMPT.format(
        admissions_context=full_context, 
        message=state['message'],
        history=history
    )
    answer = await call_llm(prompt)
    return {"reply": answer, "messages": [("assistant", answer)]}


async def tracking_agent(state: AdmissionsState):
    """
    Handles tracking queries.
    """
    history = format_history(state.get("messages", []))
    prompt = TRACKING_PROMPT.format(message=state['message'], history=history)
    answer = await call_llm(prompt)
    return {"reply": answer, "messages": [("assistant", answer)]}


async def department_router_agent(state: AdmissionsState):
    """
    Routes the query to a specific department head.
    """
    departments_data = AdmissionsDataService.load_departments_data()
    dept_options = "\n".join([f"- {key}: {info['name']}" for key, info in departments_data.items()])
    
    history = format_history(state.get("messages", []))
    prompt = DEPT_ROUTING_PROMPT.format(
        dept_options=dept_options, 
        message=state['message'],
        history=history
    )
    dept_key = (await call_llm(prompt)).strip().lower()
    
    matched_key = "not_department"
    if dept_key in departments_data or dept_key == "placements":
        matched_key = dept_key
    else:
        words = re.split(r'[^a-zA-Z0-9_]', dept_key)
        for key in list(departments_data.keys()) + ["placements"]:
            if key in words or key in dept_key:
                matched_key = key
                break
    
    if matched_key == "placements":
        return {"dept_route": "placements"} 
    
    if matched_key in departments_data:
        return {"dept_route": matched_key}
    
    if dept_key == "ambiguous":
        return {
            "dept_route": "not_department", 
            "reply": "I'm sorry, I'm not sure which department or branch you're referring to. Could you please specify? (e.g., CSE, IT, ECE, EEE, etc.)"
        }
    
    return {
        "dept_route": "not_department", 
        "reply": "I'm sorry, I couldn't identify a specific department for your query. Could you please specify which branch you are interested in?"
    }


async def admin_agent(state: AdmissionsState):
    """
    Handles admin actions.
    """
    history = format_history(state.get("messages", []))
    prompt = ADMIN_PROMPT.format(message=state['message'], history=history)
    answer = await call_llm(prompt)
    return {"reply": answer, "messages": [("assistant", answer)]}


def create_department_agent(dept_key: str, departments_data: Dict[str, Any]):
    """
    Factory function to create a node function for a specific department.
    """
    dept_info = departments_data[dept_key]
    dept_content = dept_info['content']
    dept_name = dept_info['name']

    async def department_agent(state: AdmissionsState):
        history = format_history(state.get("messages", []))
        prompt = DEPT_HEAD_PROMPT.format(
            dept_name=dept_name, 
            dept_content=dept_content, 
            message=state['message'],
            history=history
        )
        answer = await call_llm(prompt)
        return {"reply": answer, "messages": [("assistant", answer)]}
    
    return department_agent
