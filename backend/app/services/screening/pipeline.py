"""스크리닝 파이프라인 오케스트레이터"""
import uuid
from datetime import datetime, timezone

from app.services.provider.base import IDataProvider
from app.services.screening.universe_filter import (
    MOCK_UNIVERSE,
    DEFAULT_FILTERS,
    apply_universe_filter,
)
from app.services.screening.scorer import rank_candidates


def run_screening(
    provider: IDataProvider,
    filters: dict | None = None,
    top_n: int = 5,
    use_mock_universe: bool = True,
) -> dict:
    """
    전체 스크리닝 파이프라인 실행.

    흐름:
      1. 유니버스 후보 수집 (provider 또는 mock)
      2. 기본 요건 필터 적용 (시총, 거래량, 영업이익, ADR, 부도)
      3. 복합 스코어 계산 및 상위 N개 선정
      4. 결과 패키징

    Returns:
        screening result dict (screening_summary 포함)
    """
    run_at = datetime.now(timezone.utc).isoformat()
    run_id = f"sr_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    effective_filters = {**DEFAULT_FILTERS, **(filters or {})}

    # 1) 후보 수집
    if use_mock_universe:
        candidates = MOCK_UNIVERSE
    else:
        candidates = provider.get_universe_candidates(effective_filters)

    # 2) 필터 적용
    passed, excluded_by_filter = apply_universe_filter(candidates, effective_filters)

    # 3) 스코어링 및 선정
    selected, unselected = rank_candidates(passed, top_n=top_n)

    # 4) 결과 패키징
    filters_applied = []
    if effective_filters.get("min_market_cap_usd_b"):
        filters_applied.append(f"market_cap_min_{effective_filters['min_market_cap_usd_b']}B")
    if effective_filters.get("require_operating_income"):
        filters_applied.append("operating_income_positive")
    if effective_filters.get("exclude_adr"):
        filters_applied.append("no_adr")
    if effective_filters.get("exclude_bankruptcy"):
        filters_applied.append("no_bankruptcy_risk")

    all_excluded = excluded_by_filter + unselected

    return {
        "run_id": run_id,
        "run_at": run_at,
        "filters_applied": filters_applied,
        "total_candidates": len(candidates),
        "passed_filter_count": len(passed),
        "excluded_by_filter_count": len(excluded_by_filter),
        "selected_count": len(selected),
        "unselected_from_passed_count": len(unselected),
        "selected": [
            {
                "ticker": s["ticker"],
                "company_name": s["company_name"],
                "sector": s["sector"],
                "score": s["score"],
                "sector_discount_pct": s.get("sector_discount_pct"),
                "catalyst_met_count": s.get("catalyst_met_count"),
                "risk_level_max": s.get("risk_level_max"),
            }
            for s in selected
        ],
        "excluded": [
            {
                "ticker": e["ticker"],
                "company_name": e["company_name"],
                "sector": e["sector"],
                "exclusion_reason": e.get("exclusion_reason", "unknown"),
                "score": e.get("score"),
            }
            for e in all_excluded
        ],
        # screening_summary 형식 (review task 호환)
        "screening_summary": {
            "total_candidates": len(candidates),
            "selected_count": len(selected),
            "excluded_count": len(excluded_by_filter),
            "run_at": run_at,
            "filters_applied": filters_applied,
        },
    }
