# agents/core_modules.py

from typing import Any, Dict, List, Optional
from core.llm import gemini_llm
from core.db import engine, AsyncSessionLocal
from sqlalchemy import text, select
import json
import asyncio
import re
import uuid

from models.dashboard_snapshot import DashboardSnapshot
from models.resume_analysis_cache import ResumeAnalysisCache

class LLMService:
    """
    Concrete implementation of the agent's LLM interface.
    """
    def __init__(self):
        self.llm = gemini_llm

    def invoke_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        """
        Uses with_structured_output if the schema is a Pydantic model.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            structured_llm = self.llm.with_structured_output(schema)
            return structured_llm.invoke(messages)
        except Exception as e:
            # Some providers/models intermittently fail structured tool-calling.
            # Fallback: force plain JSON output and validate it against schema.
            fallback_prompt = (
                f"{user_prompt}\n\n"
                "IMPORTANT: Return ONLY a valid JSON object that matches the required schema. "
                "Do not wrap it in markdown/code fences and do not include extra text."
            )
            raw = self.llm.invoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": fallback_prompt},
            ])
            try:
                payload = self._extract_json_payload(getattr(raw, "content", raw))
                return self._coerce_schema(schema, payload)
            except Exception:
                # Preserve original failure context if fallback parsing fails.
                raise e

    def _coerce_schema(self, schema: Any, payload: Dict[str, Any]) -> Any:
        if hasattr(schema, "model_validate"):
            return schema.model_validate(payload)
        return schema(**payload)

    def _extract_json_payload(self, content: Any) -> Dict[str, Any]:
        text_content = self._normalize_content(content)

        # Handle Groq-style tool failure echoes if they leak into text.
        function_match = re.search(
            r"<function=[^>]+>\s*(\{.*\})\s*</function>",
            text_content,
            flags=re.DOTALL,
        )
        if function_match:
            return json.loads(function_match.group(1))

        fenced_match = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text_content, flags=re.DOTALL)
        if fenced_match:
            return json.loads(fenced_match.group(1))

        start = text_content.find("{")
        end = text_content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text_content[start : end + 1])

        raise ValueError("No JSON object found in model response.")

    def _normalize_content(self, content: Any) -> str:
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            parts: List[str] = []
            for item in content:
                if isinstance(item, dict) and "text" in item:
                    parts.append(str(item["text"]))
                else:
                    parts.append(str(item))
            return "\n".join(parts)
        return str(content)

    def invoke_text(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generic text-in, text-out call.
        """
        response = self.llm.invoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return response.content

    async def ainvoke_text(self, system_prompt: str, user_prompt: str) -> str:
        """
        Asynchronous version of invoke_text.
        """
        response = await self.llm.ainvoke([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])
        return response.content

    async def ainvoke_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        """
        Asynchronous version of invoke_structured.
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            structured_llm = self.llm.with_structured_output(schema)
            return await structured_llm.ainvoke(messages)
        except Exception as e:
            fallback_prompt = (
                f"{user_prompt}\n\n"
                "IMPORTANT: Return ONLY a valid JSON object that matches the required schema. "
                "Do not wrap it in markdown/code fences and do not include extra text."
            )
            raw = await self.llm.ainvoke([
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": fallback_prompt},
            ])
            try:
                payload = self._extract_json_payload(getattr(raw, "content", raw))
                return self._coerce_schema(schema, payload)
            except Exception:
                raise e

class AuditRepo:
    """
    Persists agent events to the audit_logs table.
    """
    def __init__(self):
        self.engine = engine

    async def persist_events(self, events: List[Dict[str, Any]]) -> None:
        if not events:
            return
        
        async with self.engine.begin() as conn:
            for event in events:
                try:
                    # Map event keys to audit_log columns
                    query = text("""
                        INSERT INTO audit_logs (event_type, user_id, agent_name, details)
                        VALUES (:event_type, :user_id, :agent_name, :details)
                    """)
                    # Ensure details are JSON serializable (handle UUIDs)
                    details = event.get("details", {})
                    def serialize_special(obj):
                        if isinstance(obj, uuid.UUID):
                            return str(obj)
                        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

                    await conn.execute(query, {
                        "event_type": event.get("event_type", "info"),
                        "user_id": event.get("user_id"),
                        "agent_name": event.get("agent_name", "unknown"),
                        "details": json.dumps(details, default=serialize_special)
                    })
                except Exception as e:
                    print(f"ERROR: Could not persist audit event to DB: {e}")
                    # Silently continue so the user still gets their answer
                    continue

    def persist(self, events: List[Dict[str, Any]]) -> None:
        """Synchronous wrapper for persist_events if needed by some nodes."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # If we are in an async loop, we should ideally use await
                # But if a node is sync, this is a fallback.
                loop.create_task(self.persist_events(events))
            else:
                loop.run_until_complete(self.persist_events(events))
        except Exception as e:
            print(f"Error persisting audit logs: {e}")

from core.mail import email_service

class EmailService:
    """
    Real email service for mail_automation agent.
    """
    def send_email(self, recipients: List[str], subject: str, body: str) -> bool:
        return email_service.send_email(recipients, subject, body)

class SQLRepo:
    """
    Executes read-only SQL queries and provides faculty directory data from Postgres.
    """
    def __init__(self):
        self.engine = engine

    async def execute_read_only(self, sql_query: str, sql_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        if not sql_query.strip().lower().startswith("select"):
            raise ValueError("Only SELECT statements are allowed.")

        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(text(sql_query), sql_params or {})
                return [dict(row._mapping) for row in result.all()]
        except Exception as e:
            print(f"Error executing read-only SQL: {e}")
            return []

    async def load_faculty_directory(
        self,
        *,
        interpreted_entities: Optional[Dict[str, Any]] = None,
        intent: Optional[str] = None,
        user_query: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        interpreted_entities = interpreted_entities or {}
        filters = []
        params: Dict[str, Any] = {}

        faculty_name = interpreted_entities.get("faculty_name")
        if faculty_name:
            filters.append("p.full_name ILIKE :faculty_name")
            params["faculty_name"] = f"%{faculty_name}%"

        department = interpreted_entities.get("department")
        if department:
            filters.append("f.department_id = :department_id")
            params["department_id"] = department # Assuming ID is passed or handled

        subject = interpreted_entities.get("subject_name") or interpreted_entities.get("subject")
        if subject:
            filters.append("(s.activity ILIKE :subject OR s.activity ILIKE :subject_alt)")
            params["subject"] = f"%{subject}%"
            params["subject_alt"] = f"%{subject}%"

        room = interpreted_entities.get("room_no") or interpreted_entities.get("room")
        if room:
            filters.append("f.cabin ILIKE :room")
            params["room"] = f"%{room}%"

        if not filters and user_query:
            filters.append(
                "(p.full_name ILIKE :q OR f.designation ILIKE :q OR f.cabin ILIKE :q OR s.activity ILIKE :q)"
            )
            params["q"] = f"%{user_query}%"

        where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
        rows = await self.execute_read_only(
            f"""
            SELECT
                f.id,
                p.full_name AS name,
                f.department_id,
                f.cabin,
                f.designation,
                s.day,
                s.time_range,
                s.activity
            FROM faculty f
            LEFT JOIN profiles p ON p.id = f.profile_id
            LEFT JOIN faculty_schedule_entries s ON s.faculty_id = f.id
            {where_clause}
            ORDER BY name, s.day, s.time_range
            """,
            params,
        )

        grouped: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            faculty_id = str(row["id"])
            record = grouped.setdefault(
                faculty_id,
                {
                    "id": faculty_id,
                    "name": row.get("name"),
                    "department": row.get("department_id"),
                    "cabin": row.get("cabin"),
                    "designation": row.get("designation"),
                    "schedule": {},
                },
            )
            if row.get("day") and row.get("activity"):
                record["schedule"].setdefault(row["day"], []).append(
                    f"{row['time_range']}: {row['activity']}"
                )

        return list(grouped.values())

class AnalyticsRepo:
    """
    Placeholder for chart_generator analytics data.
    """
    def get_base_dataframe(self) -> Any:
        import pandas as pd
        # Return a mock or real DB-backed dataframe
        return pd.DataFrame([
            {"department": "CSE", "month": "Jan", "placements_count": 12, "avg_package": 8.1, "offers_count": 15, "company": "A"},
            {"department": "ECE", "month": "Jan", "placements_count": 9, "avg_package": 6.9, "offers_count": 10, "company": "A"},
        ])

class DashboardRepo:
    """
    DB-backed repository for live_dashboard data.
    """
    async def load_dashboard_snapshot(self) -> Dict[str, Any]:
        async with AsyncSessionLocal() as session:
            snapshot = await session.scalar(
                select(DashboardSnapshot).order_by(DashboardSnapshot.updated_at.desc()).limit(1)
            )
            if snapshot is None:
                return {"kpis": {}, "charts": {}}

            data = snapshot.data or {}
            return {
                "kpis": {
                    "total_students": snapshot.total_students,
                    "placed_students": snapshot.placed_students,
                    "placement_rate": snapshot.placement_rate,
                    "average_package": snapshot.avg_package,
                },
                "charts": {
                    "department_wise_placements": {
                        "title": "Department-wise Placements",
                        "rows": [
                            {"department": dept, "placed_students": count}
                            for dept, count in (data.get("dept_wise") or {}).items()
                        ],
                    },
                    "month_wise_offers": {
                        "title": "Month-wise Offers",
                        "rows": [
                            {"month": month, "offers": count}
                            for month, count in (data.get("monthly_offers") or {}).items()
                        ],
                    },
                    "company_wise_hires": {
                        "title": "Company-wise Hires",
                        "rows": [
                            {"company": company, "students": count}
                            for company, count in (data.get("company_hires") or {}).items()
                        ],
                    },
                },
            }

class ResumeCacheRepo:
    """
    DB-backed cache for resume feedback.
    """
    async def get(self, resume_id: str) -> Optional[Dict[str, Any]]:
        async with AsyncSessionLocal() as session:
            record = await session.scalar(
                select(ResumeAnalysisCache).where(ResumeAnalysisCache.resume_id == resume_id)
            )
            return record.analysis if record else None

    async def put(self, resume_id: str, analysis: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        async with AsyncSessionLocal() as session:
            record = await session.scalar(
                select(ResumeAnalysisCache).where(ResumeAnalysisCache.resume_id == resume_id)
            )
            if record is None:
                record = ResumeAnalysisCache(
                    id=metadata.get("cache_id") or metadata.get("id") or str(uuid.uuid4()),
                    resume_id=resume_id,
                    analysis=analysis,
                )
                session.add(record)
            else:
                record.analysis = analysis
            await session.commit()
