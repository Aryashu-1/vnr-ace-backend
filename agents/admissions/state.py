# agents/admissions/state.py

from typing import TypedDict, Optional, Annotated, List
from langgraph.graph.message import add_messages

class AdmissionsState(TypedDict):
    message: str              # the latest user message
    messages: Annotated[List, add_messages] # the entire conversation history
    reply: Optional[str]
    route: Optional[str]      # e.g., 'department_query', 'faq'
    dept_route: Optional[str] # specific department key
