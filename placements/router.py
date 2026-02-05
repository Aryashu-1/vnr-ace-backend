from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from core.db import get_db
from core.deps import role_required
from core.auth import get_current_user
from ace_graphs import placements_graph
# Import all graphs dynamically or by name
from ace_graphs.placements_graph import (
    dashboard_graph, resume_graph, prep_graph, 
    shortlisting_graph, tracking_graph, notification_graph
)

router = APIRouter(prefix="/placements", tags=["Placements"])

# Map graph_id to actual graph object
GRAPH_MAP = {
    "dashboard": dashboard_graph,
    "resume": resume_graph,
    "prep": prep_graph,
    "shortlisting": shortlisting_graph,
    "tracking": tracking_graph,
    "notification": notification_graph,
}

@router.get("/admin")
async def admin_access(user = Depends(role_required("admin"))):
    return {"message": "Placements Admin Access", "user": user.email}

@router.get("/student")
async def student_access(user = Depends(role_required("student"))):
    return {"message": "Placements Student Access", "user": user.email}

@router.post("/chat/{graph_id}")
async def placements_chat(
    graph_id: str,
    body: dict,
    # current_user=Depends(get_current_user), # Bypassing for testing
    # db: AsyncSession = Depends(get_db)
):
    """
    Invokes the specific graph identified by graph_id.
    """
    if graph_id not in GRAPH_MAP:
        raise HTTPException(status_code=404, detail="Graph not found")
        
    target_graph = GRAPH_MAP[graph_id]

    message = body.get("message")
    if not message:
        # Default message if none provided (some widgets might just be 'triggers')
        message = "trigger"

    # Mock user for testing
    current_user_id = 999
    current_user_role = "student"

    # Prepare graph state
    initial_state = {
        "user_id": current_user_id,
        "role": current_user_role, 
        "message": message,
        "intent": graph_id, # Intent is implicit in the endpoint
        "authorized": False, 
        "response": None,
        "validation_status": None
    }

    # Run graph
    result = await target_graph.ainvoke(initial_state)

    return {
        "reply": result.get("response"),
        "graph": graph_id
    }

# ---------------------------
#   NEW FEATURE ENDPOINTS
# ---------------------------

@router.post("/upload-resume")
async def upload_resume(file: UploadFile = File(...)):
    """
    Mock resume analysis endpoint.
    In reality, this would extract text and send to LLM.
    """
    return {
        "filename": file.filename,
        "analysis": "Resume Analysis Successful.\n\nStrengths: Good project diversity.\nWeaknesses: Formatting could be cleaner.\nScore: 8/10"
    }

@router.get("/dashboard-stats")
async def get_dashboard_stats():
    """
    Returns mock live data for the dashboard.
    """
    return {
        "stats": [
            {"label": "Total Placements", "value": "156", "trend": 18},
            {"label": "Avg Package", "value": "10-15 LPA", "trend": 5},
            {"label": "Active Offers", "value": "34", "trend": -2},
            {"label": "Placement Rate", "value": "92%", "trend": 1},
        ],
        "recent_placements": [
            {"name": "John Doe", "branch": "CSE", "company": "TechCorp", "package": "12 LPA"},
            {"name": "Jane Smith", "branch": "IT", "company": "Global Sol", "package": "10 LPA"},
            {"name": "Alice Brown", "branch": "ECE", "company": "Hardware Inc", "package": "8 LPA"},
        ]
    }

@router.get("/companies")
async def get_companies():
    return ["Google", "Microsoft", "Amazon", "TCS", "Infosys", "Wipro", "Accenture"]

@router.post("/shortlist")
async def shortlist_students(
    jd: str = Form(...),
    min_gpa: float = Form(None),
    branch: str = Form(None)
):
    """
    Mock shortlisting logic based on JD and criteria.
    """
    # Mock result list
    all_students = [
        {"id": 1, "name": "Student A", "gpa": 9.0, "branch": "CSE", "match": "95%"},
        {"id": 2, "name": "Student B", "gpa": 8.5, "branch": "IT", "match": "88%"},
        {"id": 3, "name": "Student C", "gpa": 7.5, "branch": "ECE", "match": "70%"},
        {"id": 4, "name": "Student D", "gpa": 8.8, "branch": "CSE", "match": "90%"},
    ]
    
    # Simple filtering
    filtered = []
    for s in all_students:
        if min_gpa and s["gpa"] < min_gpa:
            continue
        if branch and branch.lower() not in s["branch"].lower() and branch.lower() != "all":
            continue
        filtered.append(s)
        
    return {"matches": filtered}
