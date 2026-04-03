# agents/placements/resume_feedback/constants.py

AGENT_NAME = "placements_resume_feedback"

ALLOWED_ROLES = {"student", "placement_coordinator", "tpo", "admin"}

ALLOWED_INTENTS = {
    "analyze_resume",
    "resume_followup",
    "resume_improve_section",
    "resume_score_explanation",
}

STANDARD_MESSAGES = {
    "access_denied": "You are not authorized to use the Resume Feedback Agent.",
    "out_of_scope": (
        "I can only help with resume analysis, resume feedback, follow-up questions "
        "about resume strengths/weaknesses, and resume improvement suggestions."
    ),
    "unsafe_language": (
        "Your request cannot be processed because it contains unsafe, manipulative, or policy-violating language."
    ),
    "clarification_prefix": "I need one clarification before continuing:",
    "no_resume": "No resume was provided or linked in the current request.",
    "cached_used": "Using previously stored resume analysis for follow-up.",
    "analysis_complete": "Resume analysis completed successfully.",
}

CACHE_TTL_HOURS = 24 * 14  # 14 days
MAX_MEMORY_ITEMS = 20

COLLEGE_RESUME_RULES = """
1.  **Format**: Professional layout, single page (mandatory for freshers).
2.  **Contact Info**: Name, Phone, Professional Email, LinkedIn, and GitHub (if technical). No profile photos.
3.  **Education**: Reverse chronological order. Include degree, college/school name, year of passing, and CGPA/Percentage.
4.  **Experience/Internships**: Reverse chronological order. Use action verbs (e.g., Developed, Optimized, Managed).
5.  **Projects**: Minimum of 2 relevant projects. Include title, tech stack used, and brief description of your contribution.
6.  **Skills**: Categorize skills (e.g., Programming Languages, Web Technologies, Databases, Tools).
7.  **Content**: Quantify achievements (e.g., "Reduced latency by 30%","Managed a team of 5"). Avoid generic phrases.
8.  **General**: Consistent font, size (10-12pt), and professional tone. No spelling or grammar errors.
"""