# agents/placements/chart_generator/constants.py

AGENT_NAME = "placements_chart_generator"

ALLOWED_ROLES = {"placement_coordinator", "tpo", "admin"}

ALLOWED_INTENTS = {
    "generate_chart",
    "modify_chart",
    "explain_chart",
}

ALLOWED_CHART_TYPES = {
    "bar",
    "line",
    "pie",
    "scatter",
    "histogram",
    "stacked_bar",
}

ALLOWED_METRICS = {
    "placements_count",
    "placed_students",
    "unplaced_students",
    "avg_package",
    "highest_package",
    "offers_count",
    "company_count",
    "department_wise_placements",
    "batch_wise_placements",
    "month_wise_offers",
}

ALLOWED_DIMENSIONS = {
    "department",
    "batch",
    "month",
    "company",
    "role",
    "placement_status",
}

STANDARD_MESSAGES = {
    "access_denied": "You are not authorized to use the Chart Generator Agent.",
    "out_of_scope": (
        "I can only help generate and explain placement-related charts."
    ),
    "unsafe_language": (
        "Your request cannot be processed because it contains unsafe or policy-violating language."
    ),
    "clarification_prefix": "I need one clarification before generating the chart:",
    "no_data": "No matching data was found for the requested chart.",
    "chart_generated": "Chart generated successfully.",
    "chart_not_ready": "No previously generated chart context is available for that follow-up.",
}