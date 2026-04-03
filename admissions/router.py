from fastapi import APIRouter, Depends, HTTPException
from core.deps import role_required
from agents.admissions.graph import admissions_graph

router = APIRouter(prefix="/admissions", tags=["Admissions"])

@router.get("/admin")
async def admin_endpoint(user = Depends(role_required("admin"))):
    return {"message": "Admissions Admin Access", "user": user.email}

@router.get("/faculty")
async def faculty_endpoint(user = Depends(role_required("faculty"))):
    return {"message": "Admissions Faculty Access", "user": user.email}

@router.get("/student")
async def student_endpoint(user = Depends(role_required("student"))):
    return {"message": "Admissions Student Access", "user": user.email}

@router.post("/chat")
async def admissions_chat(body: dict):
    """
    Invokes the admissions graph for handling public inquiries.
    """
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
        
    initial_state = {
        "message": message,
        "reply": None,
        "route": None,
        "dept_route": None
    }
    
    try:
        result = await admissions_graph.ainvoke(initial_state)
        return {
            "reply": result.get("reply"),
            "route": result.get("route"),
            "dept_route": result.get("dept_route")
        }
    except Exception as e:
        print(f"Error in admissions chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
