from fastapi import FastAPI, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime

from core.auth import router as auth_router
from routes.admissions import router as admissions_router
from legacy.classwork.router import router as classwork_router
from legacy.placements.router import router as placements_router
from routes.test_rbac import router as test_rbac_router
from routes.api_router import router as build_api_router
from routes.v1.api import api_v1_router

from core.deps import role_required
from core.db import engine, Base
from core.llm import LLMServiceError

# IMPORTANT: import models so metadata registers
from models.profile import Profile
from models.user_role import UserRole
from models.student import Student
from models.company import Company
from models.placement import Placement
from models.offer import Offer
from models.minor_degree import MinorDegree
from models.job_notification import JobNotification
from models.company_prep import CompanyPrepQuestion
from models.placement_drive import PlacementDrive
from models.placement_offer_v2 import PlacementOfferV2
from models.dashboard_snapshot import DashboardSnapshot
from models.department import Department

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database connected successfully")
        
        # Initialize Admissions Data Cache
        from agents.admissions.services import AdmissionsDataService
        from agents.admissions.graph import invalidate_admissions_graph
        await AdmissionsDataService.fetch_departments_from_db()
        invalidate_admissions_graph()
        print("✓ Admissions data cache initialized from DB")
    except Exception as e:
        print(f"⚠ Warning: Database connection failed: {e}")
        print("⚠ App will start without database (classwork module uses Excel files)")

    yield

app = FastAPI(
    title="VNR-ACE Backend",
    lifespan=lifespan
)

@app.exception_handler(LLMServiceError)
async def llm_service_error_handler(request: Request, exc: LLMServiceError):
    headers = {}
    if exc.retry_after is not None:
        headers["Retry-After"] = str(exc.retry_after)

    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=headers,
    )

# ---------------------------
# 🚀 CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "https://vnr-ace.vercel.app"
    ],
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=86400,
)

# ---------------------------
# 🚀 Root
# ---------------------------
@app.get("/")
def root():
    return {"status": "running", "message": "VNR-ACE backend is live!", "version": "1.0.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# ---------------------------
# 🚀 Example Admin Protected Route
# ---------------------------
@app.get("/admin/test")
async def admin_test(user = Depends(role_required("admin"))):
    return {"message": "Admin access granted", "user": user.email}

# ---------------------------
# 🚀 Static Files (Artifacts)
# ---------------------------
from fastapi.staticfiles import StaticFiles
import os

# Ensure artifacts directory exists
if not os.path.exists("artifacts"):
    os.makedirs("artifacts")
    os.makedirs("artifacts/classwork_reports")

app.mount("/artifacts", StaticFiles(directory="artifacts"), name="artifacts")

# ---------------------------
# 🚀 Routers
# ---------------------------
# Version 1 Router (New Standard)
app.include_router(api_v1_router)

# Legacy Routers (Keep for compatibility during migration)
app.include_router(auth_router)
app.include_router(admissions_router)
app.include_router(classwork_router)
app.include_router(placements_router)
app.include_router(test_rbac_router)
app.include_router(build_api_router)
