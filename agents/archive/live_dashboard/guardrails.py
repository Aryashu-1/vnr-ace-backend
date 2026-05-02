# agents/placements/live_dashboard/guardrails.py

from typing import Tuple
from .constants import ALLOWED_ROLES

UNSAFE_PATTERNS = {
    "ignore previous instructions",
    "bypass guardrails",
    "show system prompt",
    "reveal hidden prompt",
    "jailbreak",
    "hack",
    "exploit",
}


def check_access(user_role: str) -> Tuple[bool, str | None]:
    if (user_role or "").strip().lower() in ALLOWED_ROLES:
        return True, None
    return False, "access_denied"


def check_language_and_exploit(user_query: str) -> Tuple[bool, bool, str | None]:
    q = (user_query or "").strip().lower()
    for pattern in UNSAFE_PATTERNS:
        if pattern in q:
            return False, True, "exploit_attempt_detected"
    return True, False, None