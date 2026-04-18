# agents/classwork/report_generation/constants.py

AGENT_NAME = "classwork_report_generation"

ALLOWED_ROLES = {"faculty", "hod"}

ALLOWED_REPORT_TYPES = {
    "student_list",
    "attendance_report",
    "performance_report",
    "defaulter_report",
    "subject_summary",
    "section_summary",
}

ALLOWED_EXPORT_FORMATS = {"csv", "xlsx"}

DEFAULT_EXPORT_FORMAT = "xlsx"
DEFAULT_PREVIEW_LIMIT = 20

DATASET_REGISTRY = {
    "students": "db.students",
    "attendance": "db.attendance",
    "marks": "db.marks",
}

DATASET_ALLOWED_COLUMNS = {
    "students": {
        "student_id",
        "roll_no",
        "name",
        "full_name",
        "branch",
        "department",
        "section",
        "semester",
        "current_year",
        "regulation",
        "batch",
        "gender",
        "cgpa",
        "backlogs",
        "email",
    },
    "attendance": {
        "student_id",
        "subject",
        "attendance_percent",
    },
    "marks": {
        "student_id",
        "subject",
        "internal_marks",
        "external_marks",
        "total_marks",
    },
}

STANDARD_MESSAGES = {
    "access_denied": (
        "You are not authorized to use the Report Generation Agent. "
        "This feature is restricted to faculty and HOD users only."
    ),
    "out_of_scope": (
        "I can only help with classwork report generation, student list generation, "
        "attendance summaries, marks/performance reports, section summaries, and related academic reporting."
    ),
    "unsafe_language": (
        "Your request cannot be processed because it contains unsafe, manipulative, "
        "or policy-violating language."
    ),
    "clarification_prefix": "I need one clarification before generating the report:",
    "approval_prefix": "Preview is ready and awaiting approval.",
    "validation_failed": "The report could not be generated because validation failed.",
}
