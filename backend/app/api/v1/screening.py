"""스크리닝 API 엔드포인트 — 공개(public) 엔드포인트만 포함.

스크리닝 실행(run)은 Admin 전용이므로 admin.py로 이전됨.
  Admin: POST /api/v1/admin/screening/run
  Public: GET /api/v1/screening/universe
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/screening/universe")
async def get_mock_universe():
    """Mock 유니버스 전체 후보 목록 반환 (공개)."""
    from app.services.screening.universe_filter import MOCK_UNIVERSE
    return {"data": MOCK_UNIVERSE}
