from fastapi import APIRouter, Depends, HTTPException
from core.deps import role_required
# from core.auth import get_current_user # Commented out DB dependency
from ace_graphs.classwork_graph import classwork_graph
from typing import Optional

router = APIRouter(prefix="/classwork", tags=["Classwork"])

# MOCK User to bypass DB requirements for Excel mode
class MockUser:
    def __init__(self):
        self.id = 1
        self.role_id = 4 # Admin-like role or Student
        self.email = "mock_admin@vnr.edu.in"

async def get_mock_user():
    return MockUser()

@router.get("/faculty")
async def faculty_access(user = Depends(role_required("faculty"))):
    return {"message": "Classwork Faculty Access", "user": user.email}

@router.get("/student")
async def student_access(user = Depends(role_required("student"))):
    return {"message": "Classwork Student Access", "user": user.email}

@router.post("/chat")
async def classwork_chat(
    body: dict,
    # current_user=Depends(get_current_user) # OLD DB-dependent auth
    current_user=Depends(get_mock_user)      # NEW Mock auth
):
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")

    # Prepare graph state
    initial_state = {
        "user_query": message,
        "role": current_user.role_id, 
        "context": {"user_id": current_user.id}
    }

    # Run graph
    result = await classwork_graph.ainvoke(initial_state)

    return {
        "reply": result.get("final_response"),
    }
