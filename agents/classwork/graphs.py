# agents/classwork/graphs.py

from .email_automation.graph import build_mail_graph
from .faculty_timetable_enquiry.graph import build_faculty_timetable_enquiry_graph
from .report_generation.graph import build_report_generation_graph

from agents.core_modules import LLMService, AuditRepo, EmailService, SQLRepo
from .report_generation.services import ClassworkDataRepository

# Instantiate services
llm_service = LLMService()
audit_repo = AuditRepo()
email_service = EmailService()
sql_repo = SQLRepo()
classwork_data_repo = ClassworkDataRepository()

# Build graphs
email_automation_graph = build_mail_graph(
    llm=llm_service, 
    email_service=email_service, 
    audit_repo=audit_repo,
    sql_repo=sql_repo
)

faculty_timetable_enquiry_graph = build_faculty_timetable_enquiry_graph(
    llm_service=llm_service,
    sql_repo=sql_repo,
    audit_repo=audit_repo
)

report_generation_graph = build_report_generation_graph(
    llm_service=llm_service,
    audit_repo=audit_repo,
    data_repo=classwork_data_repo,
)
