import os
import uuid
import traceback
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Body
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from core.db import get_db
from core.deps import role_required, get_current_user
from core.guardrails import check_input_guardrail, check_output_guardrail
from schemas.placements import (
    ResumeAnalysisRequest, 
    ShortlistingRequest, 
    InterviewStartRequest, 
    InterviewChatRequest,
    DashboardResponse,
    PlacementStats,
    RecentPlacement
)
from schemas.agents import ChatRequest, ChatResponse

# Agent Graphs
from ace_graphs.tp_admin_graph import tp_admin_agent
from agents.placements.graphs import (
    resume_feedback_graph,
    shortlisting_graph,
    interview_prep_graph
)
from agents.placements.interview_prep.utils import load_company_data
from agents.placements.resume_feedback.services import ResumeRAGService
from agents.placements.shortlisting.services import ShortlistingService

router = APIRouter(prefix="/placements", tags=["Placements"])

@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats():
    """
    Returns live stats for the placement dashboard.
    Falls back to mock data for now.
    """
    return DashboardResponse(
        stats=[
            PlacementStats(label="Total Placements", value="156", trend=18),
            PlacementStats(label="Avg Package", value="10.5 LPA", trend=5),
            PlacementStats(label="Active Offers", value="34", trend=-2),
            PlacementStats(label="Placement Rate", value="92%", trend=1),
        ],
        recent_placements=[
            RecentPlacement(name="Aarav Sharma", branch="CSE", company="Google", package="12.5 LPA"),
            RecentPlacement(name="Ananya Reddy", branch="CSE", company="Amazon", package="14.0 LPA"),
            RecentPlacement(name="Vikram Singh", branch="ECE", company="Microsoft", package="11.0 LPA"),
        ]
    )

@router.post("/resume/analyze")
async def analyze_resume(
    file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
    body: Optional[ResumeAnalysisRequest] = Body(None),
):
    service = ResumeRAGService()
    try:
        text_input = resume_text or (body.resume_text if body else None)

        if file:
            os.makedirs("tmp", exist_ok=True)
            temp_path = f"tmp/{file.filename}"
            content = await file.read()
            with open(temp_path, "wb") as f:
                f.write(content)
            analysis = service.analyze_resume(resume_path=temp_path)
        elif text_input:
            analysis = service.analyze_resume(resume_text=text_input)
        else:
            raise HTTPException(status_code=400, detail="Either file or resume_text must be provided")
        return analysis
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/shortlist/run")
async def run_shortlisting(
    req: Optional[ShortlistingRequest] = Body(None),
    jd_text: Optional[str] = Form(None),
    no_of_students: Optional[int] = Form(5),
    db: AsyncSession = Depends(get_db),
):
    try:
        effective_jd_text = req.jd_text if req else jd_text
        effective_top_k = req.no_of_students if req else no_of_students

        if not effective_jd_text:
            raise HTTPException(status_code=400, detail="jd_text is required")

        from agents.core_modules import LLMService
        llm = LLMService()
        service = ShortlistingService(llm=llm)

        results = service.shortlist(jd_text=effective_jd_text, top_k=effective_top_k or 5)
        if results:
            results = await service.explain_matches(effective_jd_text, results)
        return {"matches": results, "count": len(results)}
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/prep/start")
async def prep_start(req: InterviewStartRequest):
    session_id = str(uuid.uuid4())
    company_data = load_company_data(req.company)
    # Note: In a real app, you'd store this in Redis or a DB.
    # For now, we'll return the rich data to the client to hold.
    return {
        "session_id": session_id,
        "company": req.company,
        "experiences": company_data.get("experiences", []),
        "questions": company_data.get("questions", []),
        "role": company_data.get("role", "Software Engineer")
    }

@router.post("/prep/chat", response_model=ChatResponse)
async def prep_chat(req: InterviewChatRequest):
    initial_state = {
        "company": "Company", # Placeholder, ideally load from session
        "user_query": req.message,
        "session_id": req.session_id,
        "audit_events": []
    }
    result = await interview_prep_graph.ainvoke(initial_state)
    return ChatResponse(reply=result.get("response"))

@router.post("/admin/process-emails")
async def process_emails(current_user = Depends(role_required("admin"))):
    initial_state = {"messages": []}
    result = await tp_admin_agent.ainvoke(initial_state)
    final_message = result.get("messages", [])[-1].content if result.get("messages") else "No result."
    return {"status": "success", "summary": final_message}
