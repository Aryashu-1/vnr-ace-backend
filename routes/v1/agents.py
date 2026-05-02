from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from core.db import get_db
from core.deps import role_required, get_current_user
from core.guardrails import check_input_guardrail, check_output_guardrail
from core.llm import LLMServiceError
from schemas.agents import ChatRequest, ChatResponse

# Agent Graphs
from agents.admissions.graph import admissions_graph
from agents.admissions.services import AdmissionsDataService
from agents.classwork.graphs import (
    faculty_timetable_enquiry_graph,
    report_generation_graph
)
# Add other graphs as needed

router = APIRouter(prefix="/agents", tags=["Agents"])

@router.post("/admissions", response_model=ChatResponse)
async def admissions_chat(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db)
):
    if not await check_input_guardrail(req.message):
        return ChatResponse(reply="I'm sorry, I cannot process this request as it seems to violate our safety guidelines. How can I help you with VNR admissions?", route="blocked_input")

    # The messages list in state should ideally come from history, but here we provide the latest
    initial_state = {
        "message": req.message,
        "messages": [("human", req.message)],
        "reply": None,
        "route": None,
    }
    
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        # LangGraph with checkpointer will merge 'messages' automatically
        result = await admissions_graph.ainvoke(initial_state, config=config)
    except LLMServiceError:
        fallback = AdmissionsDataService.build_fallback_response(req.message)
        return ChatResponse(
            reply=fallback["reply"],
            route=fallback["route"],
            metadata={**(req.metadata or {}), "fallback": "local_admissions_data"},
        )

    reply = result.get("reply")

    if reply and not await check_output_guardrail(reply, req.message):
        return ChatResponse(reply="I'm sorry, I cannot provide a detailed response for this specific query right now. Is there something else about VNR you'd like to know?", route="blocked_output")

    return ChatResponse(
        reply=reply,
        route=result.get("route"),
        metadata=req.metadata
    )

@router.post("/classwork/faculty", response_model=ChatResponse)
async def faculty_enquiry(
    req: ChatRequest,
    current_user = Depends(get_current_user)
):
    initial_state = {
        "user_query": req.message,
        "user_role": current_user.role.name if hasattr(current_user, 'role') else "student",
        "user_id": current_user.id,
        "messages": [("human", req.message)],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": req.thread_id}}
    result = await faculty_timetable_enquiry_graph.ainvoke(initial_state, config=config)
    
    return ChatResponse(
        reply=result.get("final_response"),
        metadata={"sql": result.get("sql_query")}
    )

@router.post("/classwork/report", response_model=ChatResponse)
async def report_generation(
    req: ChatRequest,
    current_user = Depends(role_required("admin"))
):
    initial_state = {
        "user_query": req.message,
        "user_role": "admin",
        "user_id": current_user.id,
        "messages": [("human", req.message)],
        "audit_events": []
    }
    
    config = {"configurable": {"thread_id": req.thread_id}}
    result = await report_generation_graph.ainvoke(initial_state, config=config)
    
    return ChatResponse(
        reply=result.get("final_response"),
        data=result.get("analysis_result"),
        artifact_path=result.get("downloadable_artifact_path")
    )
