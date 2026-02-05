from fastapi import APIRouter, Depends
from core.auth import require_role

router = APIRouter(prefix="/test", tags=["RBAC Test"])

@router.get("/admin-only")
async def admin_only(current_user = Depends(require_role(1))):
    return {"message": "Admin access OK"}

