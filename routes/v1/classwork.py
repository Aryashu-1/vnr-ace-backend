import traceback
from fastapi import APIRouter, Depends, HTTPException

from core.deps import get_current_user, role_required
from agents.classwork.graphs import (
    email_automation_graph,
    faculty_timetable_enquiry_graph,
    report_generation_graph
)

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


@router.post("/email-automation")
async def email_automation(
    body: dict, 
    current_user=Depends(role_required("admin"))
):
    """
    Agent for drafting and sending emails.
    """
    try:
        query = body.get("message")
        if not query:
            raise HTTPException(status_code=400, detail="Message required")

        initial_state = {
            "user_query": query,
            "user_role": "admin",
            "user_id": current_user.id,
            "messages": [],
            "audit_events": []
        }
        
        if body.get("approval"):
            initial_state["human_approved"] = body.get("approval") == "approved"
            # Allow manual overrides during approval
            if body.get("recipients"):
                initial_state["recipients"] = body.get("recipients")
            if body.get("subject"):
                initial_state["subject"] = body.get("subject")
            if body.get("body"):
                initial_state["body"] = body.get("body")

        result = await email_automation_graph.ainvoke(initial_state)
        return {
            "reply": result.get("final_response"),
            "state": {
                "recipients": result.get("recipients"),
                "subject": result.get("subject"),
                "body": result.get("body"),
                "approval_required": result.get("approval_required"),
                "email_sent": result.get("email_sent")
            }
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Email automation failed: {str(e)}")


@router.post("/report-generation")
async def report_generation(
    body: dict, 
    current_user=Depends(role_required("admin"))
):
    """
    Agent for generating complex reports and analyzing data.
    """
    try:
        query = body.get("message")
        if not query:
            raise HTTPException(status_code=400, detail="Message required")

        thread_id = body.get("thread_id", f"report_gen_{current_user.id}")
        initial_state = {
            "user_query": query,
            "user_role": "admin",
            "user_id": current_user.id,
            "messages": [("human", query)],
            "audit_events": []
        }
        
        # Detect approval keywords
        if query.lower() in ["approved", "yes", "proceed", "confirm", "approve"]:
            initial_state["human_approved"] = True
        
        config = {"configurable": {"thread_id": thread_id}}
        result = await report_generation_graph.ainvoke(initial_state, config=config)
        return {
            "reply": result.get("final_response"),
            "data": result.get("analysis_result"),
            "artifact_path": result.get("downloadable_artifact_path"),
            "waiting_for_human": result.get("waiting_for_human")
        }
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Report generation failed: {str(e)}")
