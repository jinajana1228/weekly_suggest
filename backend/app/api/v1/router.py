from fastapi import APIRouter
from app.api.v1 import reports, archive, chart, admin, screening

api_router = APIRouter()

api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(archive.router, tags=["archive"])
api_router.include_router(chart.router, tags=["chart"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(screening.router, tags=["screening"])
