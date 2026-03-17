from fastapi import APIRouter, Depends
from app.api.v1 import reports, archive, chart, screening
from app.api.v1 import admin
from app.api.v1.admin import require_admin

api_router = APIRouter()

api_router.include_router(reports.router, tags=["reports"])
api_router.include_router(archive.router, tags=["archive"])
api_router.include_router(chart.router, tags=["chart"])
api_router.include_router(screening.router, tags=["screening"])

# admin 라우터: include_router 단계에서 require_admin dependency를 명시적으로 적용.
# 이 방식은 APIRouter(dependencies=...) 생성자 방식과 달리
# FastAPI route table 병합 시 dependency 누락 가능성이 없다.
api_router.include_router(
    admin.router,
    tags=["admin"],
    dependencies=[Depends(require_admin)],
)
