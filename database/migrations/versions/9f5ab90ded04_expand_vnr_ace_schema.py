"""Expand VNR-ACE schema for agents and analytics

Revision ID: 9f5ab90ded04
Revises: ccd0539c0df7
Create Date: 2026-04-05 11:20:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "9f5ab90ded04"
down_revision: Union[str, Sequence[str], None] = "ccd0539c0df7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute('CREATE EXTENSION IF NOT EXISTS "pgcrypto"')

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS profiles (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            full_name TEXT NOT NULL,
            email TEXT UNIQUE,
            user_type TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'active',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS user_roles (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            profile_id TEXT NOT NULL REFERENCES profiles(id) ON DELETE CASCADE,
            role TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_roles_profile_id ON user_roles (profile_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_user_roles_role ON user_roles (role)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS departments (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            name TEXT NOT NULL UNIQUE,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS profile_id TEXT")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS department TEXT")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS section TEXT")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS current_year INTEGER")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS backlogs INTEGER DEFAULT 0")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS placement_status TEXT DEFAULT 'unplaced'")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS highest_package DOUBLE PRECISION DEFAULT 0")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS total_offers INTEGER DEFAULT 0")
    op.execute("ALTER TABLE students ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT now()")
    op.execute("CREATE INDEX IF NOT EXISTS ix_students_department ON students (department)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_students_placement_status ON students (placement_status)")

    op.execute("ALTER TABLE companies ADD COLUMN IF NOT EXISTS domain TEXT")
    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_companies_name ON companies (name)")

    op.execute("DROP TABLE IF EXISTS faculty CASCADE")
    op.execute(
        """
        CREATE TABLE faculty (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            profile_id TEXT,
            department TEXT NOT NULL,
            designation TEXT,
            cabin TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_department ON faculty (department)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS faculty_schedule_entries (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            faculty_id TEXT NOT NULL REFERENCES faculty(id) ON DELETE CASCADE,
            day TEXT NOT NULL,
            time_range TEXT NOT NULL,
            activity TEXT,
            source TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_schedule_entries_faculty_id ON faculty_schedule_entries (faculty_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_faculty_schedule_entries_day ON faculty_schedule_entries (day)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS marks (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            internal DOUBLE PRECISION,
            external DOUBLE PRECISION,
            total DOUBLE PRECISION,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_marks_student_id ON marks (student_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attendance (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT NOT NULL,
            subject TEXT NOT NULL,
            attendance_percentage DOUBLE PRECISION NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_attendance_student_id ON attendance (student_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS placement_drives (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            company_id TEXT NOT NULL,
            role TEXT NOT NULL,
            ctc DOUBLE PRECISION,
            drive_date DATE,
            status TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_drives_company_id ON placement_drives (company_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS placement_applications (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT NOT NULL,
            drive_id TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'applied',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_placement_applications_student_drive UNIQUE (student_id, drive_id)
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_applications_student_id ON placement_applications (student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_applications_drive_id ON placement_applications (drive_id)")

    op.execute("DROP TABLE IF EXISTS placement_offers CASCADE")
    op.execute(
        """
        CREATE TABLE placement_offers (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT NOT NULL,
            drive_id TEXT NOT NULL,
            offered_ctc DOUBLE PRECISION,
            accepted BOOLEAN DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_offers_student_id ON placement_offers (student_id)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_placement_offers_drive_id ON placement_offers (drive_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_experiences (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT,
            company_id TEXT NOT NULL,
            role TEXT,
            overall_experience TEXT,
            difficulty_level TEXT,
            tips TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_rounds (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            experience_id TEXT NOT NULL,
            round_type TEXT NOT NULL,
            round_order INTEGER NOT NULL,
            description TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_rounds_experience_id ON interview_rounds (experience_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS interview_questions (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            round_id TEXT NOT NULL,
            question_text TEXT NOT NULL,
            topic TEXT,
            difficulty TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_interview_questions_topic ON interview_questions (topic)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS resumes (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            student_id TEXT NOT NULL,
            file_url TEXT NOT NULL,
            extracted_text TEXT,
            metadata_json JSONB,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_resumes_student_id ON resumes (student_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_embeddings (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            resume_id TEXT NOT NULL,
            embedding JSONB,
            embedding_model TEXT,
            dimension INTEGER,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_resume_embeddings_resume_id ON resume_embeddings (resume_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS resume_analysis_cache (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            resume_id TEXT NOT NULL,
            analysis JSONB NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS ix_resume_analysis_cache_resume_id ON resume_analysis_cache (resume_id)")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS dashboard_snapshot (
            id TEXT PRIMARY KEY DEFAULT gen_random_uuid()::text,
            total_students INTEGER NOT NULL DEFAULT 0,
            placed_students INTEGER NOT NULL DEFAULT 0,
            placement_rate DOUBLE PRECISION NOT NULL DEFAULT 0,
            avg_package DOUBLE PRECISION NOT NULL DEFAULT 0,
            data JSONB NOT NULL DEFAULT '{}'::jsonb,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )


def downgrade() -> None:
    op.drop_table("dashboard_snapshot")
    op.drop_table("resume_analysis_cache")
    op.drop_table("resume_embeddings")
    op.drop_table("resumes")
    op.drop_table("interview_questions")
    op.drop_table("interview_rounds")
    op.drop_table("interview_experiences")
    op.drop_table("placement_offers")
    op.drop_table("placement_applications")
    op.drop_table("placement_drives")
    op.drop_table("attendance")
    op.drop_table("marks")
    op.drop_table("faculty_schedule_entries")
    op.drop_table("faculty")
    op.drop_table("departments")
    op.drop_table("user_roles")
    op.drop_table("profiles")
