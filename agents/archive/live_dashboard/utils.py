# agents/placements/live_dashboard/utils.py

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def make_audit_event(
    event_type: str,
    user_id: str,
    agent_name: str,
    details: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "timestamp": utc_now_iso(),
        "event_type": event_type,
        "user_id": user_id,
        "agent_name": agent_name,
        "details": details or {},
    }


def trim_memory(memory: List[Dict[str, Any]], max_items: int = 20) -> List[Dict[str, Any]]:
    return memory[-max_items:]


def summarize_charts_for_prompt(charts: Dict[str, Any]) -> Dict[str, Any]:
    summary = {}
    for key, value in (charts or {}).items():
        if isinstance(value, dict):
            summary[key] = {
                "title": value.get("title"),
                "rows_preview": value.get("rows", [])[:10],
            }
        else:
            summary[key] = value
    return summary