from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.auth import router as auth_router
from routes.admissions import router as admissions_router
from classwork.router import router as classwork_router
from placements.router import router as placements_router
from routes.test_rbac import router as test_rbac_router
from routes.api_router import router as build_api_router

from core.deps import role_required
from fastapi import FastAPI
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

app = FastAPI(title="VNR-ACE Backend")

# ---------------------------
# 🚀 CORS
# ---------------------------
origins = [
    "http://localhost:3000",
    "https://vnr-ace-frontend-gx34.vercel.app",
    "http://127.0.0.1:3000",
]

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

    # Shutdown logic (optional)
    # await engine.dispose()


app = FastAPI(lifespan=lifespan)


app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------
# 🚀 Root
# ---------------------------
@app.get("/")
def root():
    return {"status": "running", "message": "VNR-ACE backend is live!"}

# ---------------------------
# 🚀 Example Admin Protected Route
# ---------------------------
@app.get("/admin/test")
async def admin_test(user = Depends(role_required("admin"))):
    return {"message": "Admin access granted", "user": user.email}

# ---------------------------
# 🚀 Routers
# ---------------------------
app.include_router(auth_router)
app.include_router(admissions_router)
app.include_router(classwork_router)
app.include_router(placements_router)
app.include_router(test_rbac_router)
app.include_router(build_api_router)
