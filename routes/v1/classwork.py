import traceback
from fastapi import APIRouter, Depends, HTTPException

from core.deps import get_current_user
from agents.classwork.graphs import faculty_timetable_enquiry_graph

router = APIRouter(prefix="/classwork", tags=["Classwork"])


@router.post("/faculty-enquiry")
async def faculty_enquiry(
    body: dict,
    current_user=Depends(get_current_user),
):
    try:
        query = body.get("message")
        if not query:
            raise HTTPException(status_code=400, detail="Message required")

        thread_id = body.get("thread_id", f"faculty_enquiry_{current_user.id}")
        user_role = (
            current_user.role.name
            if hasattr(current_user, "role") and hasattr(current_user.role, "name")
            else "student"
        )

        initial_state = {
            "user_query": query,
            "user_role": user_role,
            "user_id": current_user.id,
            "messages": [("human", query)],
            "audit_events": [],
        }

        config = {"configurable": {"thread_id": thread_id}}
        result = await faculty_timetable_enquiry_graph.ainvoke(initial_state, config=config)
        return {
            "reply": result.get("final_response"),
            "metadata": {
                "sql": result.get("sql_query"),
                "clarification_needed": result.get("clarification_needed"),
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Faculty enquiry failed: {str(e)}")
