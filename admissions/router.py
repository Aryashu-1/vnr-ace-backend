from fastapi import APIRouter, Depends
from core.deps import role_required

router = APIRouter(prefix="/admissions", tags=["Admissions"])

@router.get("/admin")
async def admin_endpoint(user = Depends(role_required("admin"))):
    return {"message": "Admissions Admin Access", "user": user.email}

@router.get("/faculty")
async def faculty_endpoint(user = Depends(role_required("faculty"))):
    return {"message": "Admissions Faculty Access", "user": user.email}

@router.get("/student")
async def student_endpoint(user = Depends(role_required("student"))):
    return {"message": "Admissions Student Access", "user": user.email}
