# agents/placements/live_dashboard/constants.py

AGENT_NAME = "placements_live_dashboard"

ALLOWED_ROLES = {"placement_coordinator", "tpo", "admin", "hod"}

ALLOWED_INTENTS = {
    "load_dashboard",
    "dashboard_qa",
    "refresh_dashboard",
    "explain_kpi",
}

ALLOWED_KPIS = {
    "total_students",
    "eligible_students",
    "placed_students",
    "unplaced_students",
    "placement_rate",
    "total_offers",
    "average_package",
    "highest_package",
    "active_companies",
}

ALLOWED_CHARTS = {
    "department_wise_placements",
    "month_wise_offers",
    "company_wise_hires",
    "package_distribution",
    "placement_status_distribution",
}

STANDARD_MESSAGES = {
    "access_denied": "You are not authorized to use the Live Dashboard Agent.",
    "out_of_scope": "I can only help with placement dashboard metrics, charts, refresh, and related dashboard questions.",
    "unsafe_language": "Your request cannot be processed because it contains unsafe or policy-violating language.",
    "clarification_prefix": "I need one clarification before proceeding:",
    "dashboard_loaded": "Placement dashboard loaded successfully.",
    "dashboard_refreshed": "Placement dashboard refreshed successfully.",
    "dashboard_not_loaded": "Dashboard context is not available yet.",
    "no_data": "No dashboard data is available for this request.",
}