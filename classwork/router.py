from fastapi import APIRouter, Depends, HTTPException
from core.deps import role_required, get_current_user
from core.guardrails import check_input_guardrail, check_output_guardrail
from ace_graphs.classwork_graph import classwork_graph
from ace_graphs.classwork_student_graph import classwork_student_graph
from typing import Optional

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

