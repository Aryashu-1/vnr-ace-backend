from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from core.auth import router as auth_router
from routes.admissions import router as admissions_router
from classwork.router import router as classwork_router
from placements.router import router as placements_router
from routes.test_rbac import router as test_rbac_router

from core.deps import role_required
from fastapi import FastAPI
from core.db import engine, Base

# IMPORTANT: import models so metadata registers
from models.user import User
from models.role import Role

app = FastAPI(title="VNR-ACE Backend")

# ---------------------------
# 🚀 CORS
# ---------------------------
origins = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

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
