from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
from core.llm import call_llm
import pandas as pd
import os
import json

# ---------------------------
#   State Definition
# ---------------------------

class ClassworkState(TypedDict):
    user_query: str
    role: Optional[int]
    context: Optional[Dict[str, Any]]
    intent_description: Optional[str]
    raw_data: Optional[List[Dict[str, Any]]]
    final_response: Optional[str]

# ---------------------------
#   Node 1: Intent Identifier
# ---------------------------

async def intent_identifier(state: ClassworkState):
    """
    Uses LLM to understand what the user wants from their query.
    """
    query = state["user_query"]
    print(f"\n[1] Intent Identifier: Analyzing query '{query}'")
    
    prompt = f"""Analyze this student data query and describe what the user wants in 1-2 clear sentences.

Query: "{query}"

Examples of good intent descriptions:
- "User wants to see CSE students with attendance below 75%"
- "User wants to know the average CGPA of ECE students"
- "User wants to find top performers in section A"
- "User wants students with backlogs in year 2"
- "User wants general information about all students"

Intent description:"""
    
    try:
        intent = await call_llm(prompt)
        intent_clean = intent.strip()
        print(f"    -> Intent: {intent_clean}")
        return {"intent_description": intent_clean}
    except Exception as e:
        print(f"    -> Error: {e}")
        return {"intent_description": f"User wants information about: {query}"}

# ---------------------------
#   Node 2: Data Loader
# ---------------------------

async def data_loader(state: ClassworkState):
    """
    Loads all student data from Excel file.
    """
    print(f"[2] Data Loader: Loading student data from Excel")
    
    file_path = os.path.join(os.path.dirname(__file__), "../data/student_data.xlsx")
    
    try:
        df = pd.read_excel(file_path)
        data = df.to_dict(orient="records")
        print(f"    -> Loaded {len(data)} student records")
        return {"raw_data": data}
    except Exception as e:
        print(f"    -> Error loading data: {e}")
        return {"raw_data": []}

# ---------------------------
#   Node 3: LLM Processor
# ---------------------------

async def llm_processor(state: ClassworkState):
    """
    Uses LLM to filter data based on intent and generate formatted response.
    """
    intent = state["intent_description"]
    data = state["raw_data"]
    
    print(f"[3] LLM Processor: Processing {len(data)} records based on intent")
    
    # Convert data to a more readable format for LLM
    data_summary = f"Total students: {len(data)}"
    
    prompt = f"""You are a student data analyst assistant. 

User Intent: {intent}

Available Student Data Fields:
- name: Student name
- roll_number: Student roll number
- branch: Branch (CSE, ECE, MECH, CIVIL, IT, EEE)
- section: Section (A, B, C)
- year: Year (1, 2, 3, 4)
- attendance_pct: Attendance percentage (0-100)
- cumulative_gpa: CGPA (0-10)
- backlogs: Number of backlogs

Student Data ({len(data)} records):
{json.dumps(data, indent=2)}

Task:
1. Filter the student data based on the user's intent
2. Analyze the filtered results
3. Generate a clear, well-formatted response with:
   - A brief summary of findings (2-3 sentences)
   - A markdown table with relevant student details (if applicable)
   - Key insights or observations

Guidelines:
- If the query asks for specific filtering (e.g., "attendance below 75%"), apply those filters
- If the query asks for statistics (e.g., "average CGPA"), calculate and present them
- If the query is general, provide an overview
- Use markdown formatting for tables
- Be concise but informative
- Include student names, roll numbers, and relevant metrics in tables
- IMPORTANT: Your scope is strictly limited to student data and classwork. If the user asks anything outside of this scope, or if the data to answer it is not in the provided context, you MUST immediately respond exactly with: 'I cannot handle this request, out of boundary. Please ask something related to student classwork data.'

Response:"""
    
    try:
        response = await call_llm(prompt)
        print(f"    -> Generated response ({len(response)} characters)")
        return {"final_response": response.strip()}
    except Exception as e:
        print(f"    -> Error: {e}")
        return {"final_response": f"Error processing data: {str(e)}"}

# ---------------------------
#   Graph Construction
# ---------------------------

builder = StateGraph(ClassworkState)

# Add nodes
builder.add_node("intent_identifier", intent_identifier)
builder.add_node("data_loader", data_loader)
builder.add_node("llm_processor", llm_processor)

# Define flow
builder.set_entry_point("intent_identifier")
builder.add_edge("intent_identifier", "data_loader")
builder.add_edge("data_loader", "llm_processor")
builder.add_edge("llm_processor", END)

# Compile graph
classwork_graph = builder.compile()

# ---------------------------
#   Test Main Block
# ---------------------------
if __name__ == "__main__":
    import asyncio
    
    async def main():
        print(">>> Starting Simplified Classwork Graph Test <<<\n")
        
        test_queries = [
            "Show me CSE students with attendance below 75%",
            "What is the average CGPA of ECE students?",
            "Students with backlogs in year 2"
        ]
        
        for query in test_queries:
            print(f"\n{'='*80}")
            print(f"Testing: {query}")
            print('='*80)
            
            inputs = {
                "user_query": query,
                "role": 4,  # Mock student/admin role
                "context": {"user_id": 1}
            }
            
            result = await classwork_graph.ainvoke(inputs)
            
            print("\n>>> Final Response <<<")
            print(result["final_response"])
            print("\n")
        
    asyncio.run(main())
