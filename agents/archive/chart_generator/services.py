# agents/placements/chart_generator/services.py

from __future__ import annotations
from typing import Any, Dict, List


class LLMService:
    def __init__(self, llm: Any):
        self.llm = llm

    def invoke_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        raise NotImplementedError

    def invoke_text(self, system_prompt: str, user_prompt: str) -> str:
        raise NotImplementedError


class PlacementAnalyticsRepository:
    """
    This should fetch placement analytics data from DB/views.
    """

    def get_base_dataframe(self) -> Any:
        raise NotImplementedError


class AuditLogRepository:
    def __init__(self, db_client: Any):
        self.db_client = db_client

    def persist_events(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        pass