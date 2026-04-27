import os
import traceback
import uuid
from typing import Optional

from fastapi import APIRouter, Body, Depends, File, Form, HTTPException, UploadFile, status, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ace_graphs.tp_admin_graph import tp_admin_agent
from agents.placements.graphs import interview_prep_graph, resume_editor_graph, shortlisting_graph
from agents.placements.interview_prep.utils import load_company_data
from agents.placements.resume_editor.services import ResumeEditorService
from agents.placements.resume_feedback.nodes import resume_chat_node
from agents.placements.resume_feedback.services import ResumeRAGService
from agents.placements.shortlisting.services import ShortlistingService
from core.db import get_db
from core.deps import get_current_user, role_required
from models.company import Company
from models.dashboard_snapshot import DashboardSnapshot
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.profile import Profile
from models.student import Student
from schemas.agents import ChatResponse
from schemas.placements import (
    DashboardResponse,
    InterviewChatRequest,
    InterviewStartRequest,
    PlacementStats,
    RecentPlacement,
    ResumeAnalysisRequest,
    ResumeDetailResponse,
    ResumeEditRequest,
    ResumeImproveRequest,
    ResumeMutationResponse,
    ResumeReanalyzeResponse,
    ResumeUploadResponse,
    ShortlistingRequest,
    JobDetailResponse,
    ExternalRegistrationVerifyRequest,
    PolicyResponse,
    PolicyCategory,
)

router = APIRouter(prefix="/placements", tags=["Placements"])
resume_editor_service = ResumeEditorService()


class ResumeChatRequest(BaseModel):
    message: str
    structured_analysis: dict
    conversation_history: list[dict] = []


def _user_role_name(current_user) -> str:
    role = getattr(current_user, "role", None)
    if role is not None and getattr(role, "name", None):
        return role.name
    return "student"


async def _profile_id_for_current_user(db: AsyncSession, current_user) -> Optional[str]:
    profile_id = await resume_editor_service.resolve_or_create_profile_id(db, current_user)
    return str(profile_id) if profile_id else None


async def _assert_resume_access(db: AsyncSession, current_user, resume_id: str) -> None:
    role_name = _user_role_name(current_user)
    if role_name in {"admin", "tpo", "placement_coordinator"}:
        return

    profile_id = await db.scalar(select(Profile.id).where(Profile.email == current_user.email))
    resume = await resume_editor_service.fetch_resume(db, resume_id)
    if profile_id is None or (resume.user_id and str(resume.user_id) != str(profile_id)):
        raise HTTPException(status_code=403, detail="You are not allowed to access this resume.")


@router.get("/stats", response_model=DashboardResponse)
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    snapshot = await db.scalar(
        select(DashboardSnapshot).order_by(DashboardSnapshot.updated_at.desc()).limit(1)
    )
    from models.department import Department
    recent_rows = (
        await db.execute(
            select(Profile.full_name, Department.name, Company.name, PlacementOfferV2.offered_ctc)
            .join(PlacementOfferV2, PlacementOfferV2.student_id == Student.id)
            .join(PlacementDrive, PlacementDrive.id == PlacementOfferV2.drive_id)
            .join(Company, Company.id == PlacementDrive.company_id)
            .outerjoin(Profile, Profile.id == Student.profile_id)
            .outerjoin(Department, Department.id == Student.department_id)
            .order_by(PlacementOfferV2.created_at.desc())
            .limit(5)
        )
    ).all()

    if snapshot:
        stats = [
            PlacementStats(label="Total Placements", value=str(snapshot.placed_students)),
            PlacementStats(label="Avg Package", value=f"{snapshot.avg_package:.1f} LPA"),
            PlacementStats(label="Placement Rate", value=f"{snapshot.placement_rate:.1f}%"),
            PlacementStats(label="Total Students", value=str(snapshot.total_students)),
        ]
        recent_placements = [
            RecentPlacement(
                name=name or "Unknown",
                branch=branch or "Unknown",
                company=company or "Unknown",
                package=f"{(package or 0):.1f} LPA",
            )
            for name, branch, company, package in recent_rows
        ]
        return DashboardResponse(stats=stats, recent_placements=recent_placements)

    return DashboardResponse(
        stats=[
            PlacementStats(label="Total Placements", value="0"),
            PlacementStats(label="Avg Package", value="0.0 LPA"),
            PlacementStats(label="Placement Rate", value="0.0%"),
            PlacementStats(label="Total Students", value="0"),
        ],
        recent_placements=[],
    )


@router.post("/resume/upload", response_model=ResumeUploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        content = await file.read()
        profile_id = await resume_editor_service.resolve_or_create_profile_id(db, current_user)
        resume = await resume_editor_service.create_resume(
            db,
            user_id=profile_id,
            filename=file.filename or "resume.pdf",
            content=content,
        )
        analysis = await resume_editor_service.reanalyze_resume(db, resume=resume)
        await db.commit()

        detail = await resume_editor_service.build_resume_detail_payload(db, resume.id)
        return ResumeUploadResponse(
            resume_id=detail["resume_id"],
            structured_json=detail["structured_json"],
            version=detail["versions"][0],
            analysis=analysis,
        )
    except Exception as exc:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/resume/{resume_id}", response_model=ResumeDetailResponse)
async def get_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _assert_resume_access(db, current_user, resume_id)
        detail = await resume_editor_service.build_resume_detail_payload(db, resume_id)
        return ResumeDetailResponse(**detail)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/resume/{resume_id}/edit", response_model=ResumeMutationResponse)
async def edit_resume(
    resume_id: str,
    body: ResumeEditRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _assert_resume_access(db, current_user, resume_id)
        state = {
            "user_id": await _profile_id_for_current_user(db, current_user) or str(current_user.id),
            "user_role": _user_role_name(current_user),
            "user_query": body.user_instruction or f"Edit the {body.section} section truthfully.",
            "requested_action": "edit_section",
            "resume_id": resume_id,
            "section": body.section,
            "subsection_index": body.subsection_index,
            "payload": body.payload,
            "reanalyze": body.reanalyze,
            "change_summary": body.change_summary,
            "db_session": db,
            "audit_events": [],
        }
        result = await resume_editor_graph.ainvoke(state)

        if not result.get("validation_passed", True):
            await db.rollback()
            raise HTTPException(status_code=400, detail=result.get("validation_issues"))

        payload = result["response_payload"]
        return ResumeMutationResponse(
            message=result["final_response"],
            resume_id=payload["resume_id"],
            structured_json=payload["structured_json"],
            version=payload.get("version"),
            analysis=payload.get("analysis"),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/resume/{resume_id}/improve", response_model=ResumeMutationResponse)
async def improve_resume(
    resume_id: str,
    body: ResumeImproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _assert_resume_access(db, current_user, resume_id)
        instruction = body.user_instruction
        if body.action == "apply_suggestion":
            instruction = body.suggestion_text or body.user_instruction or "Apply this suggestion truthfully."
        elif not instruction:
            instruction = f"{body.action.replace('_', ' ')} for the {body.section} section without changing facts."

        state = {
            "user_id": await _profile_id_for_current_user(db, current_user) or str(current_user.id),
            "user_role": _user_role_name(current_user),
            "user_query": instruction,
            "requested_action": body.action,
            "resume_id": resume_id,
            "section": body.section,
            "subsection_index": body.subsection_index,
            "suggestion_text": body.suggestion_text,
            "reanalyze": body.reanalyze,
            "db_session": db,
            "audit_events": [],
        }
        result = await resume_editor_graph.ainvoke(state)

        if not result.get("validation_passed", True):
            await db.rollback()
            raise HTTPException(status_code=400, detail=result.get("validation_issues"))

        payload = result["response_payload"]
        return ResumeMutationResponse(
            message=result["final_response"],
            resume_id=payload["resume_id"],
            structured_json=payload["structured_json"],
            version=payload.get("version"),
            analysis=payload.get("analysis"),
        )
    except HTTPException:
        raise
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/resume/{resume_id}/reanalyze", response_model=ResumeReanalyzeResponse)
async def reanalyze_resume(
    resume_id: str,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    try:
        await _assert_resume_access(db, current_user, resume_id)
        state = {
            "user_id": await _profile_id_for_current_user(db, current_user) or str(current_user.id),
            "user_role": _user_role_name(current_user),
            "user_query": "Reanalyze this resume.",
            "requested_action": "reanalyze_resume",
            "resume_id": resume_id,
            "reanalyze": True,
            "db_session": db,
            "audit_events": [],
        }
        result = await resume_editor_graph.ainvoke(state)
        payload = result["response_payload"]
        latest_version = payload.get("versions", [None])[0]
        return ResumeReanalyzeResponse(
            resume_id=payload["resume_id"],
            analysis=payload["analysis"],
            latest_version=latest_version,
        )
    except ValueError as exc:
        await db.rollback()
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception as exc:
        await db.rollback()
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/resume/analyze")
async def analyze_resume(
    request: Request,
    file: Optional[UploadFile] = File(None),
    resume_text: Optional[str] = Form(None),
):
    service = ResumeRAGService()
    try:
        body = {}
        if request.headers.get("content-type") == "application/json":
            body = await request.json()
            
        text_input = resume_text or body.get("resume_text")

        if file:
            os.makedirs("tmp", exist_ok=True)
            temp_path = f"tmp/{file.filename}"
            content = await file.read()
            with open(temp_path, "wb") as temp_file:
                temp_file.write(content)
            analysis = service.analyze_resume(resume_path=temp_path)
        elif text_input:
            analysis = service.analyze_resume(resume_text=text_input)
        else:
            raise HTTPException(status_code=400, detail="Either file or resume_text must be provided")
        return analysis
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/shortlist/run")
async def run_shortlisting(
    req: Optional[ShortlistingRequest] = Body(None),
    jd_text: Optional[str] = Form(None),
    no_of_students: Optional[int] = Form(5),
    company: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
):
    try:
        effective_jd_text = req.jd_text if req else jd_text
        effective_top_k = req.no_of_students if req else no_of_students
        effective_company = req.company if req else company

        if not effective_jd_text:
            raise HTTPException(status_code=400, detail="jd_text is required")

        from agents.core_modules import LLMService

        llm = LLMService()
        service = ShortlistingService(llm=llm)

        results = await service.shortlist_from_db(
            db=db,
            jd_text=effective_jd_text,
            top_k=effective_top_k or 5,
            branch=req.branch if req else None,
            min_cgpa=req.min_cgpa if req else None,
        )
        if not results:
            results = service.shortlist(jd_text=effective_jd_text, top_k=effective_top_k or 5)
        if results:
            results = await service.explain_matches(effective_jd_text, results)

        company_data = load_company_data(effective_company) if effective_company else {}

        return {
            "matches": results,
            "count": len(results),
            "company": effective_company,
            "experiences": company_data.get("experiences", []),
            "questions": company_data.get("questions", []),
            "summary": company_data.get("summary"),
        }
    except HTTPException:
        raise
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/prep/start")
async def prep_start(req: InterviewStartRequest):
    session_id = str(uuid.uuid4())
    company_data = load_company_data(req.company)
    return {
        "session_id": session_id,
        "company": req.company,
        "experiences": company_data.get("experiences", []),
        "questions": company_data.get("questions", []),
        "role": company_data.get("role", "Software Engineer"),
    }


@router.post("/prep/chat", response_model=ChatResponse)
async def prep_chat(req: InterviewChatRequest):
    initial_state = {
        "company": "Company",
        "user_query": req.message,
        "session_id": req.session_id,
        "audit_events": [],
    }
    result = await interview_prep_graph.ainvoke(initial_state)
    return ChatResponse(reply=result.get("response"))


@router.post("/resume/chat")
async def resume_chat(body: ResumeChatRequest):
    state = {
        "user_id": 999,
        "user_role": "student",
        "user_query": body.message,
        "structured_analysis": body.structured_analysis,
        "conversation_history": body.conversation_history,
        "audit_events": [],
    }

    try:
        result = resume_chat_node(state)
        return {
            "reply": result.get("final_response"),
            "conversation_history": result.get("conversation_history", []),
        }
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/admin/process-emails")
async def process_emails(current_user=Depends(role_required("admin"))):
    initial_state = {"messages": []}
    result = await tp_admin_agent.ainvoke(initial_state)
    final_message = result.get("messages", [])[-1].content if result.get("messages") else "No result."
    return {"status": "success", "summary": final_message}


@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job_detail(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    drive = await db.get(PlacementDrive, job_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Job not found")

    company = await db.get(Company, drive.company_id)
    company_name = company.name if company else "Unknown"

    # Check if user has already registered externally
    profile_id = await _profile_id_for_current_user(db, current_user)
    student = await db.scalar(select(Student).where(Student.profile_id == uuid.UUID(profile_id)))
    
    is_registered_externally = False
    if student:
        application = await db.scalar(
            select(PlacementApplication).where(
                PlacementApplication.student_id == student.id,
                PlacementApplication.drive_id == job_id
            )
        )
        if application:
            is_registered_externally = application.is_registered_externally

    return JobDetailResponse(
        id=str(drive.id),
        role=drive.role,
        ctc=drive.ctc,
        company_name=company_name,
        external_registration_url=drive.external_registration_url,
        requires_external_registration=drive.requires_external_registration,
        is_registered_externally=is_registered_externally,
    )


@router.post("/jobs/{job_id}/verify-external-registration")
async def verify_external_registration(
    job_id: uuid.UUID,
    body: ExternalRegistrationVerifyRequest,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    profile_id = await _profile_id_for_current_user(db, current_user)
    student = await db.scalar(select(Student).where(Student.profile_id == uuid.UUID(profile_id)))
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    application = await db.scalar(
        select(PlacementApplication).where(
            PlacementApplication.student_id == student.id,
            PlacementApplication.drive_id == job_id
        )
    )

    if not application:
        application = PlacementApplication(
            id=str(uuid.uuid4()),
            student_id=student.id,
            drive_id=job_id,
            status="external_pending",
            is_registered_externally=True,
            external_registration_id=body.external_registration_id,
            confirmation_screenshot_url=body.confirmation_screenshot_url,
        )
        db.add(application)
    else:
        application.is_registered_externally = True
        application.external_registration_id = body.external_registration_id
        application.confirmation_screenshot_url = body.confirmation_screenshot_url
        application.status = "external_pending"

    await db.commit()
    return {"status": "success", "message": "External registration recorded for verification"}


@router.post("/apply/{job_id}")
async def apply_for_job(
    job_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user=Depends(get_current_user),
):
    drive = await db.get(PlacementDrive, job_id)
    if not drive:
        raise HTTPException(status_code=404, detail="Job not found")

    profile_id = await _profile_id_for_current_user(db, current_user)
    student = await db.scalar(select(Student).where(Student.profile_id == uuid.UUID(profile_id)))
    if not student:
        raise HTTPException(status_code=404, detail="Student profile not found")

    application = await db.scalar(
        select(PlacementApplication).where(
            PlacementApplication.student_id == student.id,
            PlacementApplication.drive_id == job_id
        )
    )

    if drive.requires_external_registration:
        if not application or not application.is_registered_externally:
            raise HTTPException(status_code=403, detail="External registration required first")

    if not application:
        application = PlacementApplication(
            id=str(uuid.uuid4()),
            student_id=student.id,
            drive_id=job_id,
            status="applied",
        )
        db.add(application)
    else:
        application.status = "applied"

    await db.commit()
    return {"status": "success", "message": "Application submitted successfully"}


@router.get("/policies", response_model=PolicyResponse)
async def get_placement_policies():
    # In a real app, these might come from a DB table 'placement_policies'
    # For now, we'll return the standard VNR policies
    return PolicyResponse(
        policies=[
            PolicyCategory(
                category="General Eligibility",
                items=[
                    "Minimum 6.5 CGPA with no active backlogs.",
                    "10th and 12th/Diploma score must be above 60%.",
                    "Students should have 75% attendance in training sessions."
                ]
            ),
            PolicyCategory(
                category="One Job Policy",
                items=[
                    "Once a student is placed in a company, they are not eligible for other companies unless the package difference is > 2 LPA.",
                    "Dream offer policy applies for packages above 10 LPA."
                ]
            ),
            PolicyCategory(
                category="Code of Conduct",
                items=[
                    "Professional attire is mandatory for all interview rounds.",
                    "Misconduct during interviews will lead to permanent debarment from placements."
                ]
            )
        ],
        last_updated=datetime.now()
    )
