from fastapi import APIRouter
from routes.v1.auth import router as auth_router
from routes.v1.analytics import router as analytics_router
from routes.v1.agents import router as agents_router
from routes.v1.classwork import router as classwork_router
from routes.v1.data import router as data_router
from routes.v1.placements import router as placements_router
from routes.api.charts import router as charts_router

api_v1_router = APIRouter(prefix="/api/v1")

api_v1_router.include_router(auth_router)
api_v1_router.include_router(analytics_router)
api_v1_router.include_router(agents_router)
api_v1_router.include_router(classwork_router)
api_v1_router.include_router(data_router)
api_v1_router.include_router(placements_router)
api_v1_router.include_router(charts_router)
