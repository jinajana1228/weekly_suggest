"""관심 가격 구간 계산 엔진

목표주가가 아님 — 섹터 중앙값 멀티플 역산 기반 조건부 참고치.
"""
from app.services.analysis.valuation import SECTOR_MEDIAN_FWD_PER


def compute_interest_range(snapshot: dict, valuation: dict | None = None) -> dict:
    """
    InterestPriceRange dict 반환.

    snapshot이 완전한 StockReport JSON이면 직접 반환.
    """
    if "interest_price_range" in snapshot:
        return snapshot["interest_price_range"]

    return _compute_from_minimal(snapshot, valuation)


def _compute_from_minimal(snap: dict, val: dict | None) -> dict:
    """섹터 중앙값 멀티플 역산으로 관심 가격 구간 추산."""
    sector = snap.get("sector", "")
    current_price = snap.get("current_price", snap.get("price", 0))

    # 기본 지표 선택
    if sector == "Financials":
        metric = "P/B"
        sector_median = 1.15
        stock_bvps = snap.get("book_value_per_share")
        if stock_bvps and sector_median:
            lower = round(stock_bvps * (sector_median * 0.9), 2)
            upper = round(stock_bvps * (sector_median * 1.1), 2)
        else:
            lower, upper = _fallback_range(current_price, 0.10)
    elif sector == "Energy":
        metric = "EV/EBITDA"
        sector_median = 7.0
        lower, upper = _fallback_range(current_price, 0.15)
    else:
        metric = "Fwd PER"
        sector_median = SECTOR_MEDIAN_FWD_PER.get(sector, 16.0)
        eps_fwd = snap.get("eps_fwd")
        if eps_fwd and sector_median:
            lower = round(eps_fwd * (sector_median * 0.90), 2)
            upper = round(eps_fwd * (sector_median * 1.05), 2)
        else:
            lower, upper = _fallback_range(current_price, 0.12)

    if sector_median and lower is not None:
        stock_val = _extract_primary_value(snap, metric)
        if stock_val and sector_median:
            discount_pct = round((sector_median - stock_val) / sector_median * 100, 1)
            stmt = (
                f"현재 {metric}는 약 {stock_val:.1f}배로 {sector} 섹터 중앙값"
                f"({sector_median:.1f}배) 대비 약 {discount_pct:.0f}% 할인 상태다. "
                f"섹터 중앙값 수준으로 멀티플이 수렴할 경우의 이론적 가격 범위는 "
                f"${lower:.2f}~${upper:.2f} 수준으로 추산된다. "
                "이는 목표주가가 아니며 밸류에이션 맥락 이해를 위한 조건부 참고치다."
            )
        else:
            stmt = (
                f"현재 가격 기준 이론적 관심 가격 범위는 ${lower:.2f}~${upper:.2f}로 추산된다. "
                "이는 목표주가가 아니며 조건부 참고치다."
            )
    else:
        stmt = "데이터 부족으로 관심 가격 구간을 산출할 수 없습니다."

    return {
        "status": "CONFIRMED" if lower else "UNAVAILABLE",
        "lower_bound": lower,
        "upper_bound": upper,
        "basis_metric": metric,
        "basis_sector_median_value": sector_median,
        "conditional_statement": stmt,
        "disclaimer": (
            "이 가격 범위는 목표주가가 아닙니다. "
            "투자 손익을 보장하지 않으며, 투자 결정의 근거로 사용해서는 안 됩니다."
        ),
    }


def _fallback_range(current: float, margin: float) -> tuple[float, float]:
    """현재가 기준 ±margin 범위."""
    if not current:
        return None, None
    return round(current * (1 - margin * 0.2), 2), round(current * (1 + margin), 2)


def _extract_primary_value(snap: dict, metric: str) -> float | None:
    mapping = {
        "Fwd PER": "fwd_per",
        "P/B": "pb",
        "EV/EBITDA": "ev_ebitda",
    }
    key = mapping.get(metric)
    return snap.get(key) if key else None
