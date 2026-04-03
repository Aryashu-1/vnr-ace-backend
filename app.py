from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime

from core.auth import router as auth_router
from routes.admissions import router as admissions_router
from classwork.router import router as classwork_router
from placements.router import router as placements_router
from routes.test_rbac import router as test_rbac_router
from routes.api_router import router as build_api_router
from routes.v1.api import api_v1_router

from core.deps import role_required
from core.db import engine, Base

# IMPORTANT: import models so metadata registers
from models.user import User
from models.role import Role
from models.student import Student
from models.company import Company
from models.placement import Placement
from models.offer import Offer
from models.minor_degree import MinorDegree
from models.job_notification import JobNotification
from models.company_prep import CompanyPrepQuestion
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✓ Database connected successfully")
    except Exception as e:
        print(f"⚠ Warning: Database connection failed: {e}")
        print("⚠ App will start without database (classwork module uses Excel files)")

    yield

app = FastAPI(
    title="VNR-ACE Backend",
    lifespan=lifespan
)

# ---------------------------
# 🚀 CORS
# ---------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"https://.*\.vercel\.app|https?://localhost(:\d+)?|https?://127\.0\.0\.1(:\d+)?|.*",
    allow_credentials=False,
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
