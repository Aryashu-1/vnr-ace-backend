from fastapi import APIRouter
from routes.v1.admin.companies import router as companies_router
from routes.v1.admin.resume_rules import router as resume_rules_router
from routes.v1.admin.records import router as records_router
from routes.v1.admin.policies import router as policies_router
from routes.v1.admin.verification import router as verification_router

admin_api_router = APIRouter(prefix="/admin")

admin_api_router.include_router(companies_router)
admin_api_router.include_router(resume_rules_router)
admin_api_router.include_router(records_router)
admin_api_router.include_router(policies_router)
admin_api_router.include_router(verification_router)
