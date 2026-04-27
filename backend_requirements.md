# Backend Requirements for New Placement Features

This document outlines the necessary backend changes to support the new features implemented in the frontend.

## 1. External Registration Support

### Objective
Allow students to register on external company portals and verify this registration before allowing them to apply through the portal.

### Model Changes
**Job Opportunity Model:**
- Add `external_registration_url` (String, nullable)
- Add `requires_external_registration` (Boolean, default: false)

**Application / Registration Model:**
- Add `is_registered_externally` (Boolean, default: false) - specifically for a user-job pair.

### API Endpoints

#### GET `/placements/jobs/{job_id}`
- **Output Structure Update:**
  ```json
  {
    "id": "string",
    "external_registration_url": "string | null",
    "requires_external_registration": "boolean",
    "is_registered_externally": "boolean"
  }
  ```

#### POST `/placements/jobs/{job_id}/verify-external-registration`
- **Purpose:** Called when a student confirms they have registered on the external portal. Ideally, this would be an automated check if the company provides an API, otherwise, it can be a manual confirmation by the student which is later verified by the placement officer.
- **Request Body:**
  ```json
  {
    "external_registration_id": "string (optional)",
    "confirmation_screenshot_url": "string (optional)"
  }
  ```
- **Output:**
  ```json
  {
    "status": "success",
    "message": "External registration recorded for verification"
  }
  ```

#### POST `/placements/apply/{job_id}`
- **Logic Update:**
  - Before processing the application, check if `requires_external_registration` is true.
  - If true, ensure `is_registered_externally` is true for the calling user.
  - If not, return `403 Forbidden` with a message: "External registration required first".

---

## 2. Placements Policy Management

### Objective
Provide dynamic placement policy content that can be updated by administrators.

### API Endpoints

#### GET `/placements/policies`
- **Output Structure:**
  ```json
  {
    "policies": [
      {
        "category": "General Eligibility",
        "items": ["string", "string"]
      },
      {
        "category": "One Job Policy",
        "items": ["string", "string"]
      }
    ],
    "last_updated": "datetime"
  }
  ```

---

## 3. Training Recommendations (Continuous Rejections)

### Objective
Provide personalized training recommendations to students who face multiple rejections.

### Logic
- Monitor student application outcomes.
- If a student reaches a threshold (e.g., 10 rejections), trigger a recommendation generation task (using AI or predefined rules).

### API Endpoints

#### GET `/profile/placement-stats`
- **Output Structure:**
  ```json
  {
    "total_applications": 14,
    "rejections": 11,
    "status": "needs_attention",
    "recommendations": [
      {
        "topic": "Data Structures & Algorithms",
        "detail": "Focus on Graph theory and DP",
        "icon": "code"
      }
    ]
  }
  ```

---

## 4. Admin Side (Internal)

### POST `/admin/placements/jobs`
- **Logic Update:** Allow setting `external_registration_url` and `requires_external_registration`.

### POST `/admin/placements/verify-student-registration`
- **Purpose:** Allow placement officers to bulk-approve or manually verify external registrations based on lists provided by companies.
