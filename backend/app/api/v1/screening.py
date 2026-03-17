"""스크리닝 API 엔드포인트"""
from fastapi import APIRouter
from pydantic import BaseModel

from app.core.config import settings
from app.services.screening.pipeline import run_screening
from app.services.provider.factory import get_provider

router = APIRouter()


class ScreeningRequest(BaseModel):
    min_market_cap_usd_b: float = 2.0
    require_operating_income: bool = True
    exclude_adr: bool = True
    exclude_bankruptcy: bool = True
    top_n: int = 5


@router.post("/screening/run")
async def run_screening_endpoint(body: ScreeningRequest | None = None):
    """
    스크리닝 파이프라인 1회 실행.
    DATA_PROVIDER_MODE=mock이면 mock universe, 실데이터 모드면 실제 screener 사용.
    """
    filters = body.model_dump() if body else {}
    top_n = filters.pop("top_n", 5)
    use_mock = settings.DATA_PROVIDER_MODE.lower() == "mock"

    result = run_screening(
        provider=get_provider(),
        filters=filters,
        top_n=top_n,
        use_mock_universe=use_mock,
    )
    return {"data": result}


@router.get("/screening/universe")
async def get_mock_universe():
    """Mock 유니버스 전체 후보 목록 반환."""
    from app.services.screening.universe_filter import MOCK_UNIVERSE
    return {"data": MOCK_UNIVERSE}
