# agents/classwork/mail_automation/constants.py

AGENT_NAME = "classwork_mail_automation"

ALLOWED_ROLES = {"faculty", "hod", "admin"}

ALLOWED_INTENTS = {
    "compose_email",
    "send_email",
    "edit_email",
}

STANDARD_MESSAGES = {
    "access_denied": "This feature is restricted to faculty and HOD users.",
    "out_of_scope": (
        "I can only help with drafting, editing, and sending academic emails "
        "(e.g., to students, sections, or faculty)."
    ),
    "unsafe_language": (
        "Your request cannot be processed due to unsafe or policy-violating language."
    ),
    "clarification_prefix": "I need one clarification before drafting the email:",
    "approval_prefix": "Draft email is ready and awaiting approval.",
    "not_approved": "Email was not sent because approval was not granted.",
    "sent_success": "Email has been sent successfully.",
}

EMAIL_DEFAULTS = {
    "signature": "Regards,\nVNR Faculty",
}