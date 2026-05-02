# agents/classwork/report_generation/services.py

from __future__ import annotations

from typing import Any, Dict, List, Optional
import pandas as pd
from sqlalchemy import select

from core.db import AsyncSessionLocal
from models.attendance import Attendance
from models.mark import Mark
from models.student import Student

from .constants import AGENT_NAME
from .schemas import PlannerOutput, ScopeClassifierOutput


class LLMService:
    """
    Adapter interface.
    Replace `invoke_structured` with your actual LangChain / Groq / OpenAI / Gemini structured output call.
    """

    def __init__(self, llm: Any):
        self.llm = llm

    def invoke_structured(self, system_prompt: str, user_prompt: str, schema: Any) -> Any:
        """
        Expected behavior:
        return an instance compatible with the pydantic schema.
        """
        # Example pseudo-code:
        # structured_llm = self.llm.with_structured_output(schema)
        # return structured_llm.invoke([
        #    {"role": "system", "content": system_prompt},
        #    {"role": "user", "content": user_prompt},
        # ])
        raise NotImplementedError("Wire this to your structured-output LLM stack.")


class AuditLogRepository:
    """
    Replace with your Supabase/Postgres implementation.
    """

    def __init__(self, db_client: Any):
        self.db_client = db_client

    def persist_events(self, events: List[Dict[str, Any]]) -> None:
        """
        Example target table: audit_logs
        Columns:
        - timestamp
        - event_type
        - user_id
        - agent_name
        - details (jsonb)
        """
        if not events:
            return

        # Example pseudo-code:
        # self.db_client.table("audit_logs").insert(events).execute()
        # or using psycopg/sqlalchemy
        pass


class ClassworkDataRepository:
    async def get_user_department_info(self, profile_id: str) -> Dict[str, Any]:
        """Fetch the department ID for a faculty member's profile."""
        from models.faculty import Faculty
        from models.department import Department
        async with AsyncSessionLocal() as session:
            # First find faculty record
            faculty_result = await session.execute(
                select(Faculty.department).where(Faculty.profile_id == profile_id)
            )
            faculty_dept_name = faculty_result.scalar_one_or_none()
            
            if not faculty_dept_name:
                return {"department_id": None, "department_name": None}
            
            # Now find department ID by name
            dept_result = await session.execute(
                select(Department.id, Department.name).where(Department.name == faculty_dept_name)
            )
            dept_info = dept_result.mappings().first()
            if dept_info:
                return {
                    "department_id": str(dept_info["id"]),
                    "department_name": dept_info["name"]
                }
            return {"department_id": None, "department_name": faculty_dept_name}

    async def load_datasets(self, dataset_names: List[str], department_id: Optional[str] = None) -> Dict[str, pd.DataFrame]:
        loaded: Dict[str, pd.DataFrame] = {}
        async with AsyncSessionLocal() as session:
            if "students" in dataset_names:
                from models.profile import Profile
                from models.department import Department
                
                stmt = select(
                    Student.id.label("student_id"),
                    Student.roll_no,
                    Profile.full_name.label("name"),
                    Profile.full_name,
                    Department.name.label("branch"),
                    Department.name.label("department"),
                    Student.section,
                    (Student.current_year * 2).label("semester"),
                    Student.current_year,
                    Student.gender,
                    Student.cgpa,
                    Student.backlogs,
                    Profile.email,
                ).outerjoin(Profile, Profile.id == Student.profile_id).outerjoin(Department, Department.id == Student.department_id)
                
                # Apply department filter if restricted
                if department_id:
                    stmt = stmt.where(Student.department_id == department_id)
                
                result = await session.execute(stmt)
                loaded["students"] = pd.DataFrame(result.mappings().all())

            if "attendance" in dataset_names:
                stmt = select(
                    Attendance.student_id.label("student_id"),
                    Attendance.subject,
                    Attendance.attendance_percentage.label("attendance_percent"),
                )
                
                # If we have a department filter, we should ideally only load attendance for those students
                if department_id:
                    stmt = stmt.join(Student, Student.id == Attendance.student_id).where(Student.department_id == department_id)
                
                result = await session.execute(stmt)
                rows = result.mappings().all()
                loaded["attendance"] = pd.DataFrame(rows, columns=["student_id", "subject", "attendance_percent"])

            if "marks" in dataset_names:
                stmt = select(
                    Mark.student_id.label("student_id"),
                    Mark.subject,
                    Mark.internal.label("internal_marks"),
                    Mark.external.label("external_marks"),
                    Mark.total.label("total_marks"),
                )
                
                if department_id:
                    stmt = stmt.join(Student, Student.id == Mark.student_id).where(Student.department_id == department_id)
                
                result = await session.execute(stmt)
                rows = result.mappings().all()
                loaded["marks"] = pd.DataFrame(
                    rows,
                    columns=["student_id", "subject", "internal_marks", "external_marks", "total_marks"],
                )

        for name in dataset_names:
            loaded.setdefault(name, pd.DataFrame())
        return loaded
