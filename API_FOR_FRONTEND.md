# VNR-ACE API Documentation for Frontend Integration

## 1. General Information
- **Base URL (Local):** `http://localhost:8000`
- **Base URL (Staging):** `https://vnr-ace-backend.onrender.com` (Example)
- **Headers:** `Content-Type: application/json` for most endpoints.
- **Authorization:** Standard Bearer token in headers: `Authorization: Bearer <access_token>`

---

## 2. Authentication
### Login
**Endpoint:** `POST /auth/login`
**Content-Type:** `application/x-www-form-urlencoded`

**Request Body:**
| Field | Type | Description |
| :--- | :--- | :--- |
| `username` | string | User email (e.g., `admin@vnr.edu.in`) |
| `password` | string | User password |

**Response:**
```json
{
  "access_token": "eyJhbGciOi...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "email": "admin@vnr.edu.in",
    "role": "admin"
  }
}
```

---

## 3. Admissions Agent (Public Inquiry)
**Endpoint:** `POST /admissions/chat`
**Goal:** Handles general inquiries about the college, departments, and admissions.

**Request Body:**
```json
{
  "message": "What are the engineering branches available?"
}
```

**Response:**
```json
{
  "reply": "VNRVJIET offers branches like CSE, IT, ECE, EEE, Civil, Mechanical, etc...",
  "route": "admissions_inquiry"
}
```

---

## 4. Classwork Agents (Faculty & Admin)
### Bulk Data Query Agent
**Endpoint:** `POST /classwork/chat`
**Required Role:** `admin`
**Goal:** Query student database for complex criteria.

**Request Body:**
```json
{
  "message": "How many students in CSE have CGPA > 8.5 and no backlogs?"
}
```

### Email Automation Agent
**Endpoint:** `POST /classwork/email-automation`
**Required Role:** `admin`
**Goal:** Drafts and Sends emails. Supports multi-turn approval.

**Request Body:**
```json
{
  "message": "Send a warning email to students with more than 3 backlogs",
  "approval": "approved" // Optional: "approved" or "rejected" for second turn
}
```

### Faculty/Timetable Enquiry Agent
**Endpoint:** `POST /classwork/faculty-enquiry`
**Goal:** Query faculty schedules and room locations.

**Request Body:**
```json
{
  "message": "Where is Dr. Ravi Kumar right now?"
}
```

### Report Generation Agent
**Endpoint:** `POST /classwork/report-generation`
**Required Role:** `admin`
**Goal:** Generates downloadable Excel/PDF reports.

**Response:**
```json
{
  "reply": "Generated the report for you.",
  "artifact_path": "/data/reports/report_123.xlsx",
  "data": [...]
}
```

---

## 5. Placement Agents
### T&P Admin Agent (Autonomous)
**Endpoint:** `POST /placements/admin/process-emails`
**Goal:** Triggers an autonomous agent that reads "pending placement emails" and updates the database.

### Placement Chat Router
**Endpoint:** `POST /placements/chat/{graph_id}`
**Graph IDs:** `dashboard`, `resume`, `prep`, `shortlisting`, `tracking`, `notification`

### Resume Feedback Agent
**Endpoint:** `POST /placements/resume-feedback`
**Goal:** Analyzes uploaded resume text and gives improvement tips.

### Shortlisting Agent
**Endpoint:** `POST /placements/shortlisting-agent`
**Required Role:** `admin` or `placement_officer`

**Request Body:**
```json
{
  "message": "Shortlist students for a Java Developer role at Amazon with min 8.0 CGPA",
  "jd_text": "Amazon is looking for Java developers..." // Optional: Full JD text
}
```

---

## 6. Direct Resume & Shortlisting APIs
These endpoints provide direct access to the logic without going through the graph/chat interface.

### Resume Analysis (Direct)
**Endpoint:** `POST /placements/resume/analyze`
**Content-Type:** `multipart/form-data`
**Goal:** Detailed ATS-style feedback on a resume.

**Request Body (Form Data):**
| Field | Type | Description |
| :--- | :--- | :--- |
| `file` | file | (Optional) PDF/DOCX/TXT resume file |
| `resume_text` | string | (Optional) Raw resume text if file is not provided |

**Response:**
```json
{
  "overall_score": 85,
  "summary": ["Strong technical background...", "Good project diversity"],
  "section_feedback": {
    "experience": {
      "issues": ["Missing metrics"],
      "suggestions": ["Add numbers to your impact"],
      "example_rewrites": ["Developed X using Y resulting in 20% increase in Z"]
    }
  },
  "ats_issues": ["Avoid triple columns"],
  "priority_fixes": ["Add GitHub links"]
}
```

### Resume Shortlisting (Direct)
**Endpoint:** `POST /placements/shortlist/run`
**Content-Type:** `application/x-www-form-urlencoded`
**Required Role:** `admin` or `placement_officer`
**Goal:** Ranks all ingested resumes against a specific Job Description.

**Request Body:**
| Field | Type | Description |
| :--- | :--- | :--- |
| `jd_text` | string | Full Job Description text |
| `top_k` | number | (Default: 5) Number of matches to return |

**Response:**
```json
{
  "matches": [
    {
      "resume_id": "student_1.pdf",
      "score": 0.92,
      "matched_chunks": [
        {"text": "...proficient in Python and FastAPI...", "score": 0.95},
        {"text": "...worked on distributed systems...", "score": 0.89}
      ]
    }
  ]
}
```

---

## 7. Analytics & Charts API
### Specific Data Endpoints
- `GET /api/charts/placement-trend`: Returns year-wise placement counts.
- `GET /api/charts/branch-wise`: Returns total vs placed counts per branch.
- `GET /api/charts/salary-distribution`: Returns counts in salary buckets.
- `GET /api/charts/multiple-offers`: Returns count of students with > 1 offer.

### Dynamic Chart Router
**Endpoint:** `POST /api/charts/dynamic`
**Goal:** Pass a question, get the correct data chart.

**Request Body:**
```json
{
  "query": "Show me how the salary is distributed"
}
```

---

## 7. AI SQL Engine
**Endpoint:** `POST /api/ai/query`
**Goal:** Natural language to live SQL results. Includes chart type suggestions.

**Request Body:**
```json
{
  "prompt": "List the top 5 students by CGPA in IT branch"
}
```

**Response:**
```json
{
  "sql": "SELECT full_name, cgpa FROM students WHERE branch='IT' ORDER BY cgpa DESC LIMIT 5",
  "result": [...],
  "chartType": "bar"
}
```

---

## 8. Data APIs (CRUD)
### Students
- `GET /api/students`: List students. Filters: `branch`, `placed` (bool), `salary_min`.
- `GET /api/students/{id}`: Get student details.

### Companies
- `GET /api/companies`: List all companies.
- `GET /api/companies/{id}`: Get company details.
- `GET /api/companies/{id}/hired_students`: List students hired by this company.

---

## 9. Test Credentials

| Role | Email | Password |
| :--- | :--- | :--- |
| **Admin** | `admin@vnr.edu.in` | `admin` |
| **Faculty** | `faculty@vnr.edu.in` | `faculty123` |
| **Student** | `student@vnr.edu.in` | `student123` |
| **Placement Officer** | `po@vnr.edu.in` | `po123` |
