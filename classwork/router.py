from fastapi import APIRouter, Depends, HTTPException
from core.deps import role_required, get_current_user
from core.guardrails import check_input_guardrail, check_output_guardrail
from ace_graphs.classwork_graph import classwork_graph
from ace_graphs.classwork_student_graph import classwork_student_graph
from typing import Optional

# New Agents
from agents.classwork.graphs import (
    email_automation_graph,
    faculty_timetable_enquiry_graph,
    report_generation_graph
)

router = APIRouter(prefix="/classwork", tags=["Classwork"])

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
    current_user=Depends(role_required("admin"))      # Requiring Admin for the Excel graph for now
):
    """
    Process natural language queries about student data.
    Supports queries about attendance, CGPA, backlogs, branches, sections, and years.
    """
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        # Input Guardrail
        if not await check_input_guardrail(message):
            return {
                "reply": "I cannot process this request as it contains inappropriate or abusive language.",
                "metadata": {"query": message, "blocked_by": "input_guardrail"}
            }

        # Prepare graph state
        initial_state = {
            "user_query": message,
            "role": current_user.role_id, 
            "context": {"user_id": current_user.id}
        }

        # Run graph
        result = await classwork_graph.ainvoke(initial_state)

        # Extract response and metadata
        final_response = result.get("final_response", "No response generated")
        
        # Output Guardrail
        if not await check_output_guardrail(final_response, message):
            return {
                "reply": "I cannot provide a response to this request as it violates safety guidelines or contains sensitive information.",
                "metadata": {"query": message, "blocked_by": "output_guardrail"}
            }

        dataset = result.get("unified_dataset", [])
        
        return {
            "reply": final_response,
            "metadata": {
                "record_count": len(dataset),
                "query": message
            }
        }
    except Exception as e:
        print(f"Error processing classwork query: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query: {str(e)}"
        )

@router.post("/student/chat")
async def student_chat(
    body: dict,
    current_user=Depends(role_required("student"))
):
    """
    Process student queries about faculty availability and room numbers.
    """
    message = body.get("message")
    if not message:
        raise HTTPException(status_code=400, detail="Message required")
    
    if not message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    try:
        # Input Guardrail
        if not await check_input_guardrail(message):
            return {
                "reply": "I cannot process this request as it contains inappropriate or abusive language.",
                "metadata": {"query": message, "blocked_by": "input_guardrail"}
            }

        # Prepare graph state
        initial_state = {
            "user_query": message,
            "role": current_user.role_id, 
            "context": {"user_id": current_user.id}
        }

        # Run graph
        result = await classwork_student_graph.ainvoke(initial_state)

        # Extract response
        final_response = result.get("final_response", "No response generated")
        
        # Output Guardrail
        if not await check_output_guardrail(final_response, message):
            return {
                "reply": "I cannot provide a response to this request as it violates safety guidelines or contains sensitive information.",
                "metadata": {"query": message, "blocked_by": "output_guardrail"}
            }
        
        return {
            "reply": final_response,
            "metadata": {
                "query": message
            }
        }
    except Exception as e:
        print(f"Error processing student query: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error processing query: {str(e)}"
        )


# ---------------------------
#   NEW AGENT ENDPOINTS
# ---------------------------

@router.post("/email-automation")
async def email_automation(body: dict, current_user=Depends(role_required("admin"))):
    """
    Agent for drafting and sending emails.
    """
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
    
    # Check if this is an approval response
    if body.get("approval"):
        initial_state["human_approved"] = body.get("approval") == "approved"
        # We need to resume the graph. For simplicity in this first version,
        # we assume the state is reconstructed or passed back. 
        # In LangGraph, we usually use a thread_id for this.
        # For now, we'll just run it with the approval.

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

@router.post("/faculty-enquiry")
async def faculty_enquiry(body: dict, current_user=Depends(get_current_user)):
    """
    Agent for faculty timetable and room inquiries.
    """
    query = body.get("message")
    if not query:
        raise HTTPException(status_code=400, detail="Message required")

    thread_id = body.get("thread_id", f"faculty_enquiry_{current_user.id}")
    initial_state = {
        "user_query": query,
        "user_role": current_user.role.name,
        "user_id": current_user.id,
        "messages": [("human", query)],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": thread_id}}
    result = await faculty_timetable_enquiry_graph.ainvoke(initial_state, config=config)
    return {
        "reply": result.get("final_response"),
        "metadata": {
            "sql": result.get("sql_query"),
            "clarification_needed": result.get("clarification_needed")
        }
    }

@router.post("/report-generation")
async def report_generation(body: dict, current_user=Depends(role_required("admin"))):
    """
    Agent for generating complex reports and analyzing data.
    """
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
    
    config = {"configurable": {"thread_id": thread_id}}
    result = await report_generation_graph.ainvoke(initial_state, config=config)
    return {
        "reply": result.get("final_response"),
        "data": result.get("analysis_result"),
        "artifact_path": result.get("downloadable_artifact_path"),
        "waiting_for_human": result.get("waiting_for_human")
    }

