import asyncio
import json
import os
import sys
import uuid
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

import fitz
from sqlalchemy import delete, func, select, text

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from core.db import AsyncSessionLocal
from models.attendance import Attendance
from models.company import Company
from models.dashboard_snapshot import DashboardSnapshot
from models.department import Department
from models.faculty import Faculty
from models.faculty_schedule_entry import FacultyScheduleEntry
from models.interview_experience import InterviewExperience
from models.interview_question import InterviewQuestion
from models.interview_round import InterviewRound
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.profile import Profile
from models.resume import Resume
from models.student import Student

DATA_DIR = ROOT / "data"
SCHEMA_SQL_FILE = ROOT / "database" / "supabase_vnr_ace_schema.sql"
FACULTY_FILE = DATA_DIR / "faculty_data.json"
CLASSWORK_STUDENTS_FILE = DATA_DIR / "classwork_students.json"
COMPANIES_FILE = DATA_DIR / "companies_sample.json"
PLACEMENTS_FILE = DATA_DIR / "placements_sample.json"
INTERVIEW_FILE = DATA_DIR / "placements" / "interview_experiences.json"
RESUMES_DIR = ROOT / "placements" / "resumes"


def read_json(path: Path):
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8"))


def extract_pdf_text(path: Path) -> str:
    try:
        doc = fitz.open(path)
        return "\n".join(page.get_text() for page in doc).strip()
    except Exception:
        return ""


def split_sql_statements(sql_text: str) -> list[str]:
    statements: list[str] = []
    current: list[str] = []
    in_single = False
    in_double = False

    for ch in sql_text:
        if ch == "'" and not in_double:
            in_single = not in_single
        elif ch == '"' and not in_single:
            in_double = not in_double

        if ch == ";" and not in_single and not in_double:
            statement = "".join(current).strip()
            if statement:
                statements.append(statement)
            current = []
            continue

        current.append(ch)

    tail = "".join(current).strip()
    if tail:
        statements.append(tail)
    return statements


async def ensure_schema() -> None:
    async with AsyncSessionLocal() as session:
        profiles_exists = await session.scalar(
            text("select to_regclass('public.profiles')")
        )
        if profiles_exists:
            return

    if not SCHEMA_SQL_FILE.exists():
        raise FileNotFoundError(f"Schema SQL file not found: {SCHEMA_SQL_FILE}")

    sql_text = SCHEMA_SQL_FILE.read_text(encoding="utf-8")
    statements = split_sql_statements(sql_text)

    from core.db import engine

    async with engine.begin() as conn:
        for statement in statements:
            await conn.execute(text(statement))


async def upsert_department(session, name: str, description: str | None = None) -> Department:
    existing = await session.scalar(select(Department).where(Department.name == name))
    if existing:
        if description and existing.description != description:
            existing.description = description
        return existing

    dept = Department(name=name, description=description)
    session.add(dept)
    await session.flush()
    return dept


async def upsert_profile(session, full_name: str, email: str | None, user_type: str) -> Profile:
    existing = None
    if email:
        existing = await session.scalar(select(Profile).where(Profile.email == email))
    if existing:
        existing.full_name = full_name
        existing.user_type = user_type
        return existing

    profile = Profile(full_name=full_name, email=email, user_type=user_type, status="active")
    session.add(profile)
    await session.flush()
    return profile


async def sync_students(session) -> dict[str, Student]:
    raw_students = read_json(CLASSWORK_STUDENTS_FILE)
    students_by_roll: dict[str, Student] = {}

    for item in raw_students:
        roll_no = str(item["roll_no"]).strip()
        full_name = item.get("name") or roll_no
        email = item.get("email")
        branch = item.get("branch")
        profile = await upsert_profile(session, full_name=full_name, email=email, user_type="student")
        if branch:
            await upsert_department(session, branch)

        student = await session.scalar(select(Student).where(Student.roll_no == roll_no))
        backlogs = int(item.get("backlogs") or 0)
        current_year = max(1, min(4, ((int(item.get("semester") or 1) + 1) // 2)))

        if student is None:
            student = Student(roll_no=roll_no)
            session.add(student)

        student.profile_id = profile.id
        student.full_name = full_name
        student.email = email
        student.branch = branch
        student.department = branch
        student.section = item.get("section")
        student.current_year = current_year
        student.cgpa = float(item.get("cgpa") or 0)
        student.backlogs = backlogs
        student.active_backlogs = backlogs
        student.passive_backlogs = 0
        student.placement_status = "unplaced"
        students_by_roll[roll_no] = student

    await session.flush()

    await session.execute(delete(Attendance))
    for student in students_by_roll.values():
        attendance_value = next(
            (row.get("attendance_percent") for row in raw_students if str(row["roll_no"]).strip() == student.roll_no),
            None,
        )
        if attendance_value is None:
            continue
        session.add(
            Attendance(student_id=student.id, subject="overall", attendance_percentage=float(attendance_value))
        )

    await session.flush()
    return students_by_roll


async def sync_companies(session) -> dict[int, Company]:
    raw_companies = read_json(COMPANIES_FILE)
    companies_by_sample_id: dict[int, Company] = {}

    for item in raw_companies:
        name = item["name"].strip()
        company = await session.scalar(select(Company).where(Company.name == name))
        if company is None:
            company = Company(name=name)
            session.add(company)
            await session.flush()
        company.sector = item.get("sector")
        company.domain = item.get("sector")
        companies_by_sample_id[int(item["id"])] = company

    return companies_by_sample_id


async def sync_faculty(session) -> None:
    raw_faculty = read_json(FACULTY_FILE)
    await session.execute(delete(FacultyScheduleEntry))
    await session.execute(delete(Faculty))

    for item in raw_faculty:
        full_name = item.get("name", "Faculty")
        profile = await upsert_profile(session, full_name=full_name, email=None, user_type="faculty")
        await upsert_department(session, item.get("department", "General"))

        faculty = Faculty(
            profile_id=profile.id,
            department=item.get("department", "General"),
            designation=item.get("designation"),
            cabin=item.get("cabin"),
        )
        session.add(faculty)
        await session.flush()

        for day, slots in (item.get("schedule") or {}).items():
            for slot in slots:
                session.add(
                    FacultyScheduleEntry(
                        faculty_id=faculty.id,
                        day=day,
                        time_range=slot.split(" (", 1)[0].strip(),
                        activity=slot,
                        source="faculty_data.json",
                    )
                )


async def sync_placements(session, students_by_roll: dict[str, Student], companies_by_sample_id: dict[int, Company]) -> None:
    raw_placements = read_json(PLACEMENTS_FILE)
    await session.execute(delete(PlacementOfferV2))
    await session.execute(delete(PlacementDrive))

    student_by_legacy_id = {}
    raw_students = read_json(CLASSWORK_STUDENTS_FILE)
    for row in raw_students:
        student = students_by_roll.get(str(row["roll_no"]).strip())
        if student:
            student_by_legacy_id[int(row["id"])] = student

    drive_keys: dict[tuple[int, float, str], PlacementDrive] = {}
    offer_counts: Counter[int] = Counter()
    highest_package: defaultdict[int, float] = defaultdict(float)

    for row in raw_placements:
        student = student_by_legacy_id.get(int(row["student_id"]))
        company = companies_by_sample_id.get(int(row["company_id"]))
        if not student or not company:
            continue

        placement_dt = datetime.fromisoformat(row["placement_date"].replace("Z", "+00:00"))
        ctc = float(row.get("ctc_lpa") or 0)
        drive_key = (company.id, ctc, placement_dt.date().isoformat())

        drive = drive_keys.get(drive_key)
        if drive is None:
            drive = PlacementDrive(
                company_id=company.id,
                role="Software Engineer",
                ctc=ctc,
                drive_date=placement_dt.date(),
                status="completed",
            )
            session.add(drive)
            await session.flush()
            drive_keys[drive_key] = drive

        session.add(
            PlacementOfferV2(
                student_id=student.id,
                drive_id=drive.id,
                offered_ctc=ctc,
                accepted=True,
            )
        )
        offer_counts[student.id] += 1
        highest_package[student.id] = max(highest_package[student.id], ctc)

    await session.flush()

    for student in students_by_roll.values():
        student.total_offers = offer_counts.get(student.id, 0)
        student.highest_package = highest_package.get(student.id, 0.0)
        student.placement_status = "placed" if student.total_offers else "unplaced"


async def sync_interview_experiences(session, companies_by_name: dict[str, Company]) -> None:
    payload = read_json(INTERVIEW_FILE)
    await session.execute(delete(InterviewQuestion))
    await session.execute(delete(InterviewRound))
    await session.execute(delete(InterviewExperience))

    for company_payload in payload.get("companies", []):
        company = companies_by_name.get(company_payload["name"].strip().lower())
        if company is None:
            continue

        for experience_index, exp in enumerate(company_payload.get("experiences", []), start=1):
            experience = InterviewExperience(
                company_id=company.id,
                role=company_payload.get("role") or "Software Engineer",
                overall_experience=exp.get("candidate"),
                difficulty_level="medium",
                tips="Imported from curated interview experience dataset.",
            )
            session.add(experience)
            await session.flush()

            for round_order, round_payload in enumerate(exp.get("rounds", []), start=1):
                round_row = InterviewRound(
                    experience_id=experience.id,
                    round_type=round_payload.get("round") or f"Round {round_order}",
                    round_order=round_order,
                    description=round_payload.get("round"),
                )
                session.add(round_row)
                await session.flush()

                for question in round_payload.get("questions", []):
                    tags = question.get("tags") or []
                    session.add(
                        InterviewQuestion(
                            round_id=round_row.id,
                            question_text=question.get("question", ""),
                            topic=", ".join(tags[:2]) if tags else None,
                            difficulty="medium",
                        )
                    )


async def sync_resumes(session, students_by_roll: dict[str, Student]) -> None:
    await session.execute(delete(Resume))
    if not RESUMES_DIR.exists():
        return

    for resume_path in RESUMES_DIR.glob("*.pdf"):
        roll_no = resume_path.stem.upper()
        student = students_by_roll.get(roll_no)
        if student is None:
            continue
        session.add(
            Resume(
                student_id=student.id,
                file_url=str(resume_path.relative_to(ROOT)).replace("\\", "/"),
                extracted_text=extract_pdf_text(resume_path),
                metadata_json={"filename": resume_path.name},
            )
        )


async def refresh_dashboard_snapshot(session) -> None:
    total_students = await session.scalar(select(func.count(Student.id))) or 0
    placed_students = await session.scalar(
        select(func.count(Student.id)).where(Student.placement_status == "placed")
    ) or 0
    avg_package = await session.scalar(
        select(func.avg(PlacementOfferV2.offered_ctc))
    ) or 0.0

    dept_rows = (
        await session.execute(
            select(Student.department, func.count(Student.id))
            .where(Student.placement_status == "placed")
            .group_by(Student.department)
        )
    ).all()
    company_rows = (
        await session.execute(
            select(Company.name, func.count(PlacementOfferV2.id))
            .join(PlacementDrive, PlacementDrive.company_id == Company.id)
            .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
            .group_by(Company.name)
            .order_by(func.count(PlacementOfferV2.id).desc())
        )
    ).all()
    month_rows = (
        await session.execute(
            select(PlacementDrive.drive_date, func.count(PlacementOfferV2.id))
            .join(PlacementOfferV2, PlacementOfferV2.drive_id == PlacementDrive.id)
            .group_by(PlacementDrive.drive_date)
            .order_by(PlacementDrive.drive_date)
        )
    ).all()

    payload = {
        "dept_wise": {dept or "Unknown": count for dept, count in dept_rows},
        "monthly_offers": {
            drive_date.strftime("%b"): count for drive_date, count in month_rows if drive_date is not None
        },
        "company_hires": {name: count for name, count in company_rows},
    }

    await session.execute(delete(DashboardSnapshot))
    session.add(
        DashboardSnapshot(
            total_students=total_students,
            placed_students=placed_students,
            placement_rate=round((placed_students / total_students) * 100, 2) if total_students else 0.0,
            avg_package=round(float(avg_package), 2) if avg_package else 0.0,
            data=payload,
        )
    )


async def main() -> None:
    await ensure_schema()

    async with AsyncSessionLocal() as session:
        students_by_roll = await sync_students(session)
        companies_by_sample_id = await sync_companies(session)
        await sync_faculty(session)
        await sync_placements(session, students_by_roll, companies_by_sample_id)
        companies_by_name = {company.name.lower(): company for company in companies_by_sample_id.values()}
        await sync_interview_experiences(session, companies_by_name)
        await sync_resumes(session, students_by_roll)
        await refresh_dashboard_snapshot(session)
        await session.commit()

    print("VNR-ACE data sync complete.")


if __name__ == "__main__":
    asyncio.run(main())
