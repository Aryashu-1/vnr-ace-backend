---
title: VNR-ACE Backend
emoji: 🚀
colorFrom: blue
colorTo: indigo
sdk: docker
app_file: app.py
pinned: false
---

# VNR-ACE Backend

VNR-ACE is an advanced AI-powered platform for campus intelligence, admissions assistance, and placement automation. 

## 🚀 Getting Started

### Prerequisites
- **Python**: 3.11+
- **Poetry**: Modern Python package manager.

### Installation
1. Clone the repository.
2. Install dependencies:
   ```bash
   poetry install
   ```
3. Set up environment variables:
   - Create a `.env` file in the root directory.
   - Required keys: `DATABASE_URL`, `GEMINI_API_KEY`, `TAVILY_API_KEY`.

### Running the Backend
To start the FastAPI server with auto-reload:
```bash
poetry run uvicorn app:app --reload
```
The server will be available at `http://localhost:8000`.

## 📂 Project Structure
- `agents/`: Structured LangGraph agent modules (Admissions, Placements, Classwork).
- `admissions/`, `placements/`, `classwork/`: FastAPI routers for different domains.
- `models/`: Database models.
- `core/`: Core utilities (Authentication, Database, Guardrails).
- `data/`: Dataset storage for departments and companies.

## 📄 Documentation
- **API for Frontend**: [API_FOR_FRONTEND.md](API_FOR_FRONTEND.md) - Detailed endpoint documentation for frontend integration.
- **DB Design**: [DB_DESIGN.md](DB_DESIGN.md) - Database schema and relationships.

## 🛠️ Maintenance
- Use `placements/resume_ingester.py` to rebuild the resume FAISS index after adding new files.
