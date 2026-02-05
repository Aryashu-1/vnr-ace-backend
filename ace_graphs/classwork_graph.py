from typing import TypedDict, Optional, List, Dict, Any
from langgraph.graph import StateGraph, END
# from core.llm import call_llm # Uncomment when integrated
import asyncio

# ---------------------------
#   State Definition
# ---------------------------

class ClassworkState(TypedDict):
    user_query: str
    role: str  # e.g., 'admin', 'student'
    context: Dict[str, Any]
    normalized_query: Optional[str]
    semantic_intent: Optional[Dict[str, Any]]
    execution_plan: Optional[Dict[str, Any]]
    unified_dataset: Optional[List[Dict[str, Any]]]
    insights: Optional[List[str]]
    final_response: Optional[str]

# ---------------------------
#   Nodes
# ---------------------------

async def academic_nlq_entry(state: ClassworkState):
    """
    1. Academic NLQ Entry
    Receives: Admin’s natural language query, Context
    Output: Cleaned query text + metadata
    """
    query = state.get("user_query", "")
    print(f"\n[1] Academic NLQ Entry: Received query '{query}'")
    
    # Basic cleaning or context injection could happen here
    context = state.get("context", {})
    context.setdefault("timestamp", "now")
    
    return {"context": context}

async def query_normalizer(state: ClassworkState):
    """
    2. Query Normalizer
    Fixes grammar, expands shorthand.
    """
    query = state["user_query"]
    print(f"[2] Query Normalizer: Normalizing '{query}'")
    
    # Placeholder for LLM-based normalization
    # e.g., normalized = await call_llm(f"Normalize: {query}")
    
    normalized = query
    # Simple rule-based logic for the demo
    if "low att" in normalized.lower():
        normalized = normalized.replace("low att", "low attendance")
    
    # Example logic: "top performers" -> "top 10% by GPA" 
    # (Not implementing all rules, just structure)
    
    print(f"    -> Normalized: '{normalized}'")
    return {"normalized_query": normalized}

async def schema_intent_mapper(state: ClassworkState):
    """
    3. Schema & Intent Mapper
    Maps natural language to academic schema.
    """
    normalized = state["normalized_query"]
    print(f"[3] Schema & Intent Mapper: Mapping '{normalized}'")
    
    intent = {
        "metrics": [],
        "filters": {},
        "group_by": []
    }
    
    norm_lower = normalized.lower()
    
    # Rule-based Mapping
    if "attendance" in norm_lower:
        intent["metrics"].append("attendance_percentage")
    if "cgpa" in norm_lower or "grades" in norm_lower:
        intent["metrics"].append("cumulative_gpa")
    
    if "cse" in norm_lower:
        intent["filters"]["branch"] = "CSE"
    if "2nd year" in norm_lower:
        intent["filters"]["year"] = 2
        
    print(f"    -> Intent: {intent}")
    return {"semantic_intent": intent}

async def query_planner(state: ClassworkState):
    """
    4. Query Planner
    Builds a logical plan: Which datasets? Join strategy?
    """
    intent = state["semantic_intent"]
    print(f"[4] Query Planner: Building plan for {intent}")
    
    plan = {
        "datasets": ["student_metadata"], # Always need metadata
        "operations": []
    }
    
    metrics = intent.get("metrics", [])
    if "attendance_percentage" in metrics:
        plan["datasets"].append("attendance_table")
    if "cumulative_gpa" in metrics:
        plan["datasets"].append("marks_table")
        
    print(f"    -> Plan: {plan}")
    return {"execution_plan": plan}

import pandas as pd
import os

async def data_fetcher(state: ClassworkState):
    """
    5. Data Fetcher
    Executes the plan, fetches raw data from Excel.
    """
    plan = state["execution_plan"]
    print(f"[5] Data Fetcher: Fetching datasets {plan['datasets']}")
    
    # Path to Excel file
    file_path = os.path.join(os.path.dirname(__file__), "../data/student_data.xlsx")
    
    try:
        # Read Excel using pandas
        df = pd.read_excel(file_path)
        data = df.to_dict(orient="records")
        print(f"    -> Loaded {len(data)} records from Excel")
        return {"unified_dataset": data}
    except Exception as e:
        print(f"    -> Error loading data: {e}")
        # Fallback to empty list or mock if needed, but error is better for debugging
        return {"unified_dataset": []}

async def aggregation_reasoning_engine(state: ClassworkState):
    """
    6. Aggregation & Reasoning Engine
    Filtering, Aggregation, Trend detection, Risk scoring.
    """
    intent = state["semantic_intent"]
    data = state["unified_dataset"]
    print(f"[6] Aggregation Engine: Processing {len(data)} records")
    
    filters = intent.get("filters", {})
    
    # 1. Apply Filters
    filtered_data = []
    for s in data:
        match = True
        if "branch" in filters and s["branch"] != filters["branch"]:
            match = False
        if "year" in filters and s["year"] != filters["year"]:
            match = False
        if match:
            filtered_data.append(s)
            
    # 2. Reasoning / Risk Scoring
    # Logic: "Students with attendance < 70% AND CGPA < 6" (derived from query usually, here inferred for demo logic)
    # We will compute a 'risk_score' based on the metrics requested.
    
    processed_data = []
    for s in filtered_data:
        risk_score = 0
        reasons = []
        
        # Example thresholds
        if s["attendance_pct"] < 75:
            risk_score += 1
            reasons.append("Low Attendance")
        if s["cumulative_gpa"] < 6.0:
            risk_score += 1
            reasons.append("Low CGPA")
            
        s["risk_score"] = risk_score
        s["risk_reasons"] = reasons
        
        # If the query implies looking for 'problems' (risk), we might filter by risk > 0
        # For now, let's keep all matching filters but sort by risk.
        processed_data.append(s)
        
    # Sort by risk score descending
    processed_data.sort(key=lambda x: x["risk_score"], reverse=True)
    
    print(f"    -> {len(processed_data)} records remaining after filter.")
    return {"unified_dataset": processed_data}

async def insight_generator(state: ClassworkState):
    """
    7. Insight Generator
    Transforms numbers into meaning.
    """
    data = state["unified_dataset"]
    print(f"[7] Insight Generator: Analyzing data")
    
    insights = []
    
    # Pattern identification
    high_risk_students = [s for s in data if s["risk_score"] >= 2]
    
    if high_risk_students:
        insights.append(f"{len(high_risk_students)} students in this group show critical performance drops (Risk Score >= 2).")
        names = ", ".join([s["name"] for s in high_risk_students])
        insights.append(f"Students requiring immediate attention: {names}.")
    elif data:
         insights.append("Overall performance appears stable for this cohort.")
    else:
        insights.append("No data found matching the specific criteria.")

    return {"insights": insights}

async def response_formatter(state: ClassworkState):
    """
    8. Response Formatter
    Output: JSON or Formatted Text
    """
    insights = state["insights"]
    data = state["unified_dataset"]
    
    print(f"[8] Response Formatter: Formatting output")
    
    nl_response = "### Academic Insights\n\n"
    for i in insights:
        nl_response += f"- {i}\n"
    
    nl_response += "\n### Student Details\n"
    nl_response += "| Name | Branch | Attendance | CGPA | Risk Factors |\n"
    nl_response += "|---|---|---|---|---|\n"
    
    for s in data:
        reasons = ", ".join(s.get("risk_reasons", [])) or "None"
        nl_response += f"| {s['name']} | {s['branch']} | {s['attendance_pct']}% | {s['cumulative_gpa']} | {reasons} |\n"
        
    return {"final_response": nl_response}

# ---------------------------
#   Graph Construction
# ---------------------------

builder = StateGraph(ClassworkState)

builder.add_node("academic_nlq_entry", academic_nlq_entry)
builder.add_node("query_normalizer", query_normalizer)
builder.add_node("schema_intent_mapper", schema_intent_mapper)
builder.add_node("query_planner", query_planner)
builder.add_node("data_fetcher", data_fetcher)
builder.add_node("aggregation_reasoning_engine", aggregation_reasoning_engine)
builder.add_node("insight_generator", insight_generator)
builder.add_node("response_formatter", response_formatter)

# Edges
builder.set_entry_point("academic_nlq_entry")
builder.add_edge("academic_nlq_entry", "query_normalizer")
builder.add_edge("query_normalizer", "schema_intent_mapper")
builder.add_edge("schema_intent_mapper", "query_planner")
builder.add_edge("query_planner", "data_fetcher")
builder.add_edge("data_fetcher", "aggregation_reasoning_engine")
builder.add_edge("aggregation_reasoning_engine", "insight_generator")
builder.add_edge("insight_generator", "response_formatter")
builder.add_edge("response_formatter", END)

classwork_graph = builder.compile()

# ---------------------------
#   Test Main Block
# ---------------------------
if __name__ == "__main__":
    async def main():
        print(">>> Starting Academic NLQ Graph Test <<<")
        
        # Test Input from User Request
        inputs = {
            "user_query": "CSE students 2nd year with low attendance and poor grades",
            "role": "admin",
            "context": {}
        }
        
        result = await classwork_graph.ainvoke(inputs)
        
        print("\n>>> Final Response <<<")
        print(result["final_response"])
        
    asyncio.run(main())
