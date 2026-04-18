create extension if not exists "pgcrypto";

create table if not exists profiles (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    email text unique,
    user_type text not null,
    status text not null default 'active',
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create table if not exists user_roles (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid not null references profiles(id) on delete cascade,
    role text not null,
    created_at timestamptz not null default now()
);

create index if not exists ix_user_roles_profile_id on user_roles(profile_id);
create index if not exists ix_user_roles_role on user_roles(role);

create table if not exists departments (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    description text,
    created_at timestamptz not null default now()
);

create table if not exists students (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id) on delete set null,
    roll_no text not null unique,
    full_name text,
    gender text,
    dob text,
    branch text,
    department text,
    section text,
    current_year integer,
    email text,
    mobile text,
    cgpa double precision,
    backlogs integer default 0,
    tenth_cgpa double precision,
    inter_percent double precision,
    active_backlogs integer default 0,
    passive_backlogs integer default 0,
    category text,
    home_town text,
    district text,
    state text,
    pincode text,
    minor_degree text,
    intern_status boolean default false,
    placement_status text default 'unplaced',
    highest_package double precision default 0,
    total_offers integer default 0,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists ix_students_roll_no on students(roll_no);
create index if not exists ix_students_branch on students(branch);
create index if not exists ix_students_department on students(department);
create index if not exists ix_students_placement_status on students(placement_status);

create table if not exists marks (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    subject text not null,
    internal double precision,
    external double precision,
    total double precision,
    created_at timestamptz not null default now()
);

create index if not exists ix_marks_student_id on marks(student_id);

create table if not exists attendance (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    subject text not null,
    attendance_percentage double precision not null,
    created_at timestamptz not null default now()
);

create index if not exists ix_attendance_student_id on attendance(student_id);

create table if not exists faculty (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id) on delete set null,
    department text not null,
    designation text,
    cabin text,
    created_at timestamptz not null default now()
);

create index if not exists ix_faculty_department on faculty(department);

create table if not exists faculty_schedule_entries (
    id uuid primary key default gen_random_uuid(),
    faculty_id uuid not null references faculty(id) on delete cascade,
    day text not null,
    time_range text not null,
    activity text,
    source text,
    created_at timestamptz not null default now()
);

create index if not exists ix_faculty_schedule_entries_faculty_id on faculty_schedule_entries(faculty_id);
create index if not exists ix_faculty_schedule_entries_day on faculty_schedule_entries(day);

create table if not exists companies (
    id uuid primary key default gen_random_uuid(),
    name text not null unique,
    sector text,
    domain text,
    created_at timestamptz not null default now()
);

create table if not exists placement_drives (
    id uuid primary key default gen_random_uuid(),
    company_id uuid not null references companies(id) on delete cascade,
    role text not null,
    ctc double precision,
    drive_date date,
    status text,
    created_at timestamptz not null default now()
);

create index if not exists ix_placement_drives_company_id on placement_drives(company_id);

create table if not exists placement_applications (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    drive_id uuid not null references placement_drives(id) on delete cascade,
    status text not null default 'applied',
    created_at timestamptz not null default now(),
    unique(student_id, drive_id)
);

create index if not exists ix_placement_applications_student_id on placement_applications(student_id);
create index if not exists ix_placement_applications_drive_id on placement_applications(drive_id);

create table if not exists placement_offers (
    id uuid primary key default gen_random_uuid(),
    student_id uuid not null references students(id) on delete cascade,
    drive_id uuid not null references placement_drives(id) on delete cascade,
    offered_ctc double precision,
    accepted boolean default true,
    created_at timestamptz not null default now()
);

create index if not exists ix_placement_offers_student_id on placement_offers(student_id);
create index if not exists ix_placement_offers_drive_id on placement_offers(drive_id);

create table if not exists interview_experiences (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete set null,
    company_id uuid not null references companies(id) on delete cascade,
    role text,
    overall_experience text,
    difficulty_level text,
    tips text,
    created_at timestamptz not null default now()
);

create table if not exists interview_rounds (
    id uuid primary key default gen_random_uuid(),
    experience_id uuid not null references interview_experiences(id) on delete cascade,
    round_type text not null,
    round_order integer not null,
    description text,
    created_at timestamptz not null default now()
);

create index if not exists ix_interview_rounds_experience_id on interview_rounds(experience_id);

create table if not exists interview_questions (
    id uuid primary key default gen_random_uuid(),
    round_id uuid not null references interview_rounds(id) on delete cascade,
    question_text text not null,
    topic text,
    difficulty text,
    created_at timestamptz not null default now()
);

create index if not exists ix_interview_questions_topic on interview_questions(topic);

create table if not exists resumes (
    id uuid primary key default gen_random_uuid(),
    user_id uuid references profiles(id) on delete cascade,
    student_id uuid not null references students(id) on delete cascade,
    file_url text not null,
    raw_text text,
    extracted_text text,
    structured_json jsonb,
    metadata_json jsonb,
    current_version_id bigint,
    created_at timestamptz not null default now()
);

create index if not exists ix_resumes_student_id on resumes(student_id);
create index if not exists ix_resumes_user_id on resumes(user_id);

create table if not exists resume_versions (
    id bigserial primary key,
    resume_id uuid not null references resumes(id) on delete cascade,
    version_number int not null,
    content jsonb not null,
    change_summary text,
    created_at timestamptz not null default now(),
    unique(resume_id, version_number)
);

create index if not exists ix_resume_versions_resume_id on resume_versions(resume_id);

create table if not exists resume_embeddings (
    id uuid primary key default gen_random_uuid(),
    resume_id uuid not null references resumes(id) on delete cascade,
    embedding jsonb,
    embedding_model text,
    dimension integer,
    created_at timestamptz not null default now()
);

create index if not exists ix_resume_embeddings_resume_id on resume_embeddings(resume_id);

create table if not exists resume_analysis_cache (
    id bigserial primary key,
    resume_id uuid not null references resumes(id) on delete cascade,
    analysis jsonb not null,
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now()
);

create index if not exists ix_resume_analysis_cache_resume_id on resume_analysis_cache(resume_id);

create table if not exists dashboard_snapshot (
    id uuid primary key default gen_random_uuid(),
    total_students integer not null default 0,
    placed_students integer not null default 0,
    placement_rate double precision not null default 0,
    avg_package double precision not null default 0,
    data jsonb not null default '{}'::jsonb,
    updated_at timestamptz not null default now()
);

create table if not exists audit_logs (
    id bigint generated always as identity primary key,
    timestamp timestamptz not null default now(),
    event_type text,
    user_id text,
    agent_name text,
    details jsonb
);

create index if not exists ix_audit_logs_event_type on audit_logs(event_type);
create index if not exists ix_audit_logs_user_id on audit_logs(user_id);
create index if not exists ix_audit_logs_agent_name on audit_logs(agent_name);
