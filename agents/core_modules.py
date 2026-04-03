# agents/core_modules.py

from typing import Any, Dict, List, Optional
from core.llm import groq_llm
from core.db import engine
from sqlalchemy import text
import json
import asyncio
import sqlite3
import os
import re

class LLMService:
    """
    Concrete implementation of the agent's LLM interface.
    """
    def __init__(self):
        self.llm = groq_llm

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
                    await conn.execute(query, {
                        "event_type": event.get("event_type", "info"),
                        "user_id": event.get("user_id"),
                        "agent_name": event.get("agent_name", "unknown"),
                        "details": json.dumps(event.get("details", {}))
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

class EmailService:
    """
    Mock email service for mail_automation agent.
    """
    def send_email(self, recipients: List[str], subject: str, body: str) -> bool:
        print(f"DEBUG: Sending email to {recipients} | Subject: {subject}")
        # In a real app, use smtplib or an API like SendGrid
        return True

class SQLRepo:
    """
    Executes SQL queries for the faculty_timetable_enquiry agent using JSON data.
    Loads data/faculty_data.json into an in-memory SQLite database.
    """
    def __init__(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self._initialize_data()

    def _initialize_data(self):
        cursor = self.db.cursor()
        
        # Create Tables
        cursor.execute("""
            CREATE TABLE faculty (
                id INTEGER PRIMARY KEY,
                name TEXT COLLATE NOCASE,
                department TEXT COLLATE NOCASE,
                cabin TEXT,
                designation TEXT
            )
        """)

        cursor.execute("""
            CREATE TABLE students (
                id INTEGER PRIMARY KEY,
                roll_no TEXT UNIQUE,
                name TEXT COLLATE NOCASE,
                branch TEXT COLLATE NOCASE,
                section TEXT,
                semester INTEGER,
                attendance_percent REAL,
                backlogs INTEGER,
                cgpa REAL,
                email TEXT
            )
        """)
        
        cursor.execute("""
            CREATE TABLE timetable (
                faculty_id INTEGER,
                day TEXT,
                time_range TEXT,
                activity TEXT,
                FOREIGN KEY (faculty_id) REFERENCES faculty(id)
            )
        """)
        
        # Load Faculty JSON
        faculty_path = os.path.join(os.path.dirname(__file__), "../data/faculty_data.json")
        if os.path.exists(faculty_path):
            with open(faculty_path, "r") as f:
                faculty_data = json.load(f)
            for item in faculty_data:
                cursor.execute(
                    "INSERT INTO faculty (id, name, department, cabin, designation) VALUES (?, ?, ?, ?, ?)",
                    (item["id"], item["name"], item["department"], item["cabin"], item["designation"])
                )
                schedule = item.get("schedule", {})
                for day, slots in schedule.items():
                    for slot in slots:
                        cursor.execute(
                            "INSERT INTO timetable (faculty_id, day, time_range, activity) VALUES (?, ?, ?, ?)",
                            (item["id"], day, slot, slot)
                        )

        # Load Student JSON
        student_path = os.path.join(os.path.dirname(__file__), "../data/classwork_students.json")
        if os.path.exists(student_path):
            with open(student_path, "r") as f:
                student_data = json.load(f)
            for item in student_data:
                cursor.execute(
                    "INSERT INTO students (id, roll_no, name, branch, section, semester, attendance_percent, backlogs, cgpa, email) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (item["id"], item["roll_no"], item["name"], item["branch"], item["section"], item["semester"], item["attendance_percent"], item["backlogs"], item["cgpa"], item["email"])
                )
        
        self.db.commit()

    async def execute_read_only(self, sql_query: str, sql_params: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        cursor = self.db.cursor()
        try:
            if sql_params:
                cursor.execute(sql_query, sql_params)
            else:
                cursor.execute(sql_query)
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]
        except Exception as e:
            print(f"Error executing in-memory SQL: {e}")
            return []

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
    Placeholder for live_dashboard data.
    """
    def get_dashboard_data(self) -> Dict[str, Any]:
        return {
            "stats": {"total_placements": 156, "avg_package": 12.5},
            "recent_activity": []
        }

class ResumeCacheRepo:
    """
    Placeholder for resume_feedback caching.
    """
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        return None
    def put(self, key: str, analysis: Dict[str, Any], metadata: Dict[str, Any]) -> None:
        pass
