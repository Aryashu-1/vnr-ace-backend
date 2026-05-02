# agents/placements/graphs.py

from agents.archive.chart_generator.graph import build_chart_generator_graph
from agents.archive.live_dashboard.graph import build_live_dashboard_graph
from .resume_feedback.graph import build_resume_feedback_graph
from .resume_editor.graph import build_resume_editor_graph
from .shortlisting.graph import build_shortlisting_graph
from .interview_prep.graph import build_interview_prep_graph
from .resume_editor.services import ResumeEditorService

from agents.core_modules import (
    LLMService, 
    AuditRepo, 
    AnalyticsRepo, 
    DashboardRepo, 
    ResumeCacheRepo
)

# Instantiate services
llm_service = LLMService()
audit_repo = AuditRepo()
analytics_repo = AnalyticsRepo()
dashboard_repo = DashboardRepo()
resume_cache_repo = ResumeCacheRepo()
resume_editor_service = ResumeEditorService()

# Build graphs
chart_generator_graph = build_chart_generator_graph(
    llm_service=llm_service,
    analytics_repo=analytics_repo,
    audit_repo=audit_repo
)

live_dashboard_graph = build_live_dashboard_graph(
    llm_service=llm_service,
    dashboard_repo=dashboard_repo,
    audit_repo=audit_repo
)

resume_feedback_graph = build_resume_feedback_graph(
    llm_service=llm_service,
    cache_repo=resume_cache_repo,
    audit_repo=audit_repo
)

resume_editor_graph = build_resume_editor_graph(
    llm_service=llm_service,
    editor_service=resume_editor_service,
)

shortlisting_graph = build_shortlisting_graph(
    llm=llm_service
)

interview_prep_graph = build_interview_prep_graph(
    llm_service=llm_service,
    audit_repo=audit_repo
)
