from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from core.llm import call_llm
import json
import os

# ---------------------------
#   State Definition
# ---------------------------

class ClassworkStudentState(TypedDict):
    user_query: str
    role: Optional[int]
    context: Optional[Dict[str, Any]]
    intent: Optional[str]
    faculty_data: Optional[List[Dict[str, Any]]]
    final_response: Optional[str]

# ---------------------------
#   Node 1: Intent Identifier
# ---------------------------

async def intent_identifier(state: ClassworkStudentState):
    """
    Identifies what the student is asking about regarding faculty.
    """
    query = state["user_query"]
    print(f"\n[Student Graph] Intent Identifier: Analyzing query '{query}'")
    
    prompt = f"""Analyze this student query about faculty and describe the intent in 1 sentence.
    
    Query: "{query}"
    
    Examples:
    - "Where is Dr. Ravi?" -> "User wants to know the location/cabin of Dr. Ravi"
    - "Is Mrs. Priya free now?" -> "User wants to check current availability of Mrs. Priya"
    - "Show me Suresh Reddy's timetable" -> "User wants the full schedule of Mr. Suresh Reddy"
    - "Who is the HOD of H&S?" -> "User wants to find faculty by designation/dept"
    
    Intent:"""
    
    try:
        intent = await call_llm(prompt)
        print(f"    -> Intent: {intent.strip()}")
        return {"intent": intent.strip()}
    except Exception as e:
        print(f"    -> Error in intent: {e}")
        return {"intent": f"User query: {query}"}

# ---------------------------
#   Node 2: Data Loader
# ---------------------------

async def data_loader(state: ClassworkStudentState):
    """
    Loads faculty data from the JSON file. 
    In a real app, this might search a DB or vector store based on the query/intent.
    """
    print(f"[Student Graph] Data Loader: Loading faculty data")
    
    file_path = os.path.join(os.path.dirname(__file__), "../data/faculty_data.json")
    
    try:
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
            print(f"    -> Loaded {len(data)} faculty records")
            return {"faculty_data": data}
        else:
            print(f"    -> Data file not found at {file_path}")
            return {"faculty_data": []}
    except Exception as e:
        print(f"    -> Error loading data: {e}")
        return {"faculty_data": []}

# ---------------------------
#   Node 3: Response Generator
# ---------------------------

async def response_generator(state: ClassworkStudentState):
    """
    Generates a natural language response based on the data and query.
    """
    intent = state["intent"]
    data = state["faculty_data"]
    query = state["user_query"]
    
    print(f"[Student Graph] Response Generator: Generating answer")
    
    # Filter data slightly to reduce context if possible, or just pass all valid JSON
    # For now, we pass the whole small dataset.
    
    prompt = f"""You are a strict and compliant assistant for students for the Classwork module. You ONLY answer questions about the provided Faculty Data.
    
    User Query: "{query}"
    Intent: {intent}
    
    Faculty Data:
    {json.dumps(data, indent=2)}
    
    Task:
    Answer the student's question based strictly on the provided Faculty Data.
    - If asking for a cabin/room, provide it.
    - If asking for availability, check the schedule for the current day (assume today is Monday if not specified, or just list the relevant day's schedule).
    - If the faculty is not found, say so politely.
    - Format usage: Use markdown (bold keys, simple lists).
    
    CRITICAL RULES:
    1. Your scope is strictly limited to Classwork and Faculty Data.
    2. If the user asks for ANYTHING outside of this scope (e.g., general knowledge, recipes, unrelated tasks), or if the data to answer it is not in the provided context, you MUST NOT attempt to answer.
    3. Instead, you MUST immediately respond EXACTLY with: 'I cannot handle this request, out of boundary. Please ask something related to the Classwork module.' AND NOTHING ELSE.
    
    Response:"""
    
    try:
        response = await call_llm(prompt)
        return {"final_response": response.strip()}
    except Exception as e:
        return {"final_response": "Sorry, I encountered an error generating the response."}

# ---------------------------
#   Graph Construction
# ---------------------------

builder = StateGraph(ClassworkStudentState)

builder.add_node("intent_identifier", intent_identifier)
builder.add_node("data_loader", data_loader)
builder.add_node("response_generator", response_generator)

builder.set_entry_point("intent_identifier")
builder.add_edge("intent_identifier", "data_loader")
builder.add_edge("data_loader", "response_generator")
builder.add_edge("response_generator", END)

classwork_student_graph = builder.compile()
