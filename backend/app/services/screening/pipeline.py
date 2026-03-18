"""스크리닝 파이프라인 오케스트레이터"""
import logging
import uuid
from datetime import datetime, timezone

from app.services.provider.base import IDataProvider
from app.services.screening.universe_filter import (
    MOCK_UNIVERSE,
    DEFAULT_FILTERS,
    apply_universe_filter,
)
from app.services.screening.scorer import rank_candidates
from app.services.analysis.valuation import compute_valuation
from app.services.analysis.catalyst import assess_catalysts
from app.services.analysis.risk import assess_risks

logger = logging.getLogger(__name__)


def _enrich_candidate_for_scoring(candidate: dict, provider: IDataProvider) -> dict:
    """
    FMP screener 기본 후보 → 스코어링 필드 보완.

    provider.get_stock_snapshot / get_consensus_data / get_earnings_calendar 를
    호출해 sector_discount_pct, week_52_position_pct, catalyst_met_count,
    risk_level_max 를 계산한다.

    각 단계가 실패해도 기본값으로 폴백 — 스코어링은 항상 실행 가능.
    """
    ticker = candidate["ticker"]
    enriched = {**candidate}

    # ── 1. 스냅샷 → 밸류에이션 + 52w 위치 ───────────────────
    snapshot = None
    try:
        snapshot = provider.get_stock_snapshot(ticker)
    except Exception as e:
        logger.warning("enrich: get_stock_snapshot 실패 %s: %s", ticker, e)

    if snapshot:
        # 기본 필드 보완 (screener 결과에 없을 수 있는 것들)
        for key in ("current_price", "industry", "short_description", "headquarters", "exchange"):
            if enriched.get(key) is None:
                enriched[key] = snapshot.get(key)

        # 52w 위치 계산
        try:
            high = float(snapshot.get("52w_high") or 0)
            low  = float(snapshot.get("52w_low")  or 0)
            price = float(snapshot.get("current_price") or enriched.get("current_price") or 0)
            if high > low > 0 and price:
                enriched["week_52_position_pct"] = round((price - low) / (high - low) * 100, 1)
            else:
                enriched.setdefault("week_52_position_pct", 50.0)
        except (TypeError, ValueError):
            enriched.setdefault("week_52_position_pct", 50.0)

        # 섹터 할인율 (valuation engine 경유)
        try:
            val  = compute_valuation(snapshot)
            disc = val.get("valuation_discount_vs_sector", {}).get("discount_pct")
            enriched["sector_discount_pct"] = disc if disc is not None else 0.0
        except Exception as e:
            logger.warning("enrich: compute_valuation 실패 %s: %s", ticker, e)
            enriched.setdefault("sector_discount_pct", 0.0)

        snap_for_analysis = {**snapshot, **enriched}
    else:
        enriched.setdefault("week_52_position_pct", 50.0)
        enriched.setdefault("sector_discount_pct",  0.0)
        snap_for_analysis = enriched

    # ── 2. 촉매 평가 ─────────────────────────────────────────
    try:
        consensus = provider.get_consensus_data(ticker)
        earnings  = provider.get_earnings_calendar(ticker, days_ahead=365)
        catalyst  = assess_catalysts(snap_for_analysis, consensus, earnings)
        enriched["catalyst_met_count"] = catalyst.get("met_count", 0)
    except Exception as e:
        logger.warning("enrich: catalyst 평가 실패 %s: %s", ticker, e)
        enriched.setdefault("catalyst_met_count", 0)

    # ── 3. 리스크 레벨 ───────────────────────────────────────
    try:
        structural, _ = assess_risks(snap_for_analysis)
        sev_rank = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}
        max_sev  = "MEDIUM"
        for r in structural:
            s = r.get("severity", "MEDIUM")
            if sev_rank.get(s, 1) > sev_rank.get(max_sev, 1):
                max_sev = s
        enriched["risk_level_max"] = max_sev
    except Exception as e:
        logger.warning("enrich: risk 평가 실패 %s: %s", ticker, e)
        enriched.setdefault("risk_level_max", "MEDIUM")

    return enriched


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
      3. [real mode] 각 후보 스코어링 필드 보완 (snapshot/consensus/earnings 호출)
      4. 복합 스코어 계산 및 상위 N개 선정
      5. 결과 패키징

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
    passed_count = len(passed)

    # 3) [real mode] 스코어링 필드 보완 (mock은 이미 pre-computed)
    if not use_mock_universe and passed:
        enriched_passed = []
        for c in passed:
            enriched_passed.append(_enrich_candidate_for_scoring(c, provider))
        passed = enriched_passed

    # 4) 스코어링 및 선정 (2-버킷: 성장/수혜 3 + 저평가 2)
    selected, unselected = rank_candidates(passed, top_n=top_n)

    # 5) 결과 패키징
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
        "passed_filter_count": passed_count,
        "excluded_by_filter_count": len(excluded_by_filter),
        "selected_count": len(selected),
        "unselected_from_passed_count": len(unselected),
        "selected": [
            {
                "ticker": s["ticker"],
                "company_name": s["company_name"],
                "sector": s["sector"],
                "score": s["score"],
                "selection_type": s.get("selection_type", "UNDERVALUED"),
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
