# agents/placements/chart_generator/utils.py

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import pandas as pd


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


def apply_filters(df: pd.DataFrame, filters: Dict[str, Any]) -> pd.DataFrame:
    result = df.copy()
    for key, value in (filters or {}).items():
        if key in result.columns:
            result = result[result[key] == value]
    return result


def ensure_output_dir(path: str | Path) -> Path:
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


def build_chart_filename(chart_type: str) -> str:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{chart_type}_chart_{ts}.png"