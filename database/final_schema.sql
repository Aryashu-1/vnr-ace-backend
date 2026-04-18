create extension if not exists "pgcrypto";
create extension if not exists "vector";


create table profiles (
    id uuid primary key default gen_random_uuid(),
    full_name text not null,
    email text unique,
    user_type text not null,
    status text default 'active',
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table user_roles (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id) on delete cascade,
    role text not null,
    created_at timestamptz default now()
);

create index ix_user_roles_profile_id on user_roles(profile_id);

create table departments (
    id uuid primary key default gen_random_uuid(),
    name text unique not null,
    description text,
    created_at timestamptz default now()
);

create table students (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id) on delete set null,
    roll_no text unique not null,
    department_id uuid references departments(id),
    section text,
    current_year int,
    cgpa numeric,
    backlogs int default 0,
    active_backlogs int default 0,
    passive_backlogs int default 0,
    tenth_cgpa numeric,
    inter_percent numeric,
    gender text,
    dob text,
    category text,
    home_town text,
    district text,
    state text,
    pincode text,
    minor_degree text,
    intern_status boolean default false,

    placement_status text default 'unplaced',
    highest_package numeric default 0,
    total_offers int default 0,

    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create index ix_students_department on students(department_id);
create index ix_students_status on students(placement_status);

create table student_skills (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    skill text not null
);

create table marks (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    subject text,
    internal numeric,
    external numeric,
    total numeric,
    created_at timestamptz default now()
);

create index ix_marks_student on marks(student_id);

create table marks (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    subject text,
    internal numeric,
    external numeric,
    total numeric,
    created_at timestamptz default now()
);

create index ix_marks_student on marks(student_id);


create table faculty (
    id uuid primary key default gen_random_uuid(),
    profile_id uuid references profiles(id),
    department_id uuid references departments(id),
    designation text,
    cabin text,
    created_at timestamptz default now()
);

create table faculty_timetable (
    id uuid primary key default gen_random_uuid(),
    faculty_id uuid references faculty(id) on delete cascade,
    day text,
    time_range text,
    subject text,
    room text,
    created_at timestamptz default now()
);

create table companies (
    id uuid primary key default gen_random_uuid(),
    name text unique not null,
    domain text,
    sector text,
    created_at timestamptz default now()
);



create table placement_drives (
    id uuid primary key default gen_random_uuid(),
    company_id uuid references companies(id) on delete cascade,
    role text,
    ctc numeric,
    drive_date date,
    status text,
    created_at timestamptz default now()
);


create table placement_applications (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    drive_id uuid references placement_drives(id) on delete cascade,
    status text check (status in ('applied','shortlisted','rejected','selected')),
    created_at timestamptz default now(),
    unique(student_id, drive_id)
);

create index ix_app_student on placement_applications(student_id);
create index ix_app_drive on placement_applications(drive_id);

create table placement_offers (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    drive_id uuid references placement_drives(id) on delete cascade,
    offered_ctc numeric,
    accepted boolean default true,
    created_at timestamptz default now(),
    unique(student_id, drive_id)
);




create table interview_experiences (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id),
    company_id uuid references companies(id),
    role text,
    overall_experience text,
    difficulty_level text,
    tips text,
    created_at timestamptz default now()
);

create index ix_exp_company on interview_experiences(company_id);

create table interview_rounds (
    id uuid primary key default gen_random_uuid(),
    experience_id uuid references interview_experiences(id) on delete cascade,
    round_type text,
    round_order int,
    description text,
    created_at timestamptz default now()
);

create table interview_questions (
    id uuid primary key default gen_random_uuid(),
    round_id uuid references interview_rounds(id) on delete cascade,
    question_text text,
    topic text,
    difficulty text,
    created_at timestamptz default now()
);

create index ix_questions_topic on interview_questions(topic);

create table resumes (
    id uuid primary key default gen_random_uuid(),
    student_id uuid references students(id) on delete cascade,
    file_url text,
    raw_text text,
    extracted_text text,
    structured_json jsonb,
    metadata_json jsonb,
    created_at timestamptz default now()
);

create table resume_versions (
    id bigserial primary key,
    resume_id uuid references resumes(id) on delete cascade,
    version_number int,
    content jsonb,
    change_summary text,
    created_at timestamptz default now(),
    unique(resume_id, version_number)
);

create table resume_embeddings (
    id uuid primary key default gen_random_uuid(),
    resume_id uuid references resumes(id) on delete cascade,
    embedding vector(384),
    embedding_model text,
    dimension int,
    created_at timestamptz default now()
);

create table resume_analysis_cache (
    id bigserial primary key,
    resume_id uuid references resumes(id) on delete cascade,
    analysis jsonb,
    created_at timestamptz default now(),
    updated_at timestamptz default now()
);

create table dashboard_snapshot (
    id uuid primary key default gen_random_uuid(),
    total_students int,
    placed_students int,
    placement_rate numeric,
    avg_package numeric,
    data jsonb,
    version int default 1,
    updated_at timestamptz default now()
);

create table placement_analytics_cache (
    id uuid primary key default gen_random_uuid(),
    metric_name text,
    data jsonb,
    created_at timestamptz default now()
);

create table audit_logs (
    id bigint generated always as identity primary key,
    timestamp timestamptz default now(),
    event_type text,
    user_id uuid references profiles(id),
    agent_name text,
    details jsonb
);