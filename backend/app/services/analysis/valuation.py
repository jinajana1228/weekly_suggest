"""밸류에이션 분석 엔진

Mock 모드: snapshot(= 전체 StockReport JSON)에서 직접 추출.
Real 모드: provider에서 받은 원시 재무 데이터를 이용해 계산.
"""
from typing import Any


# ──────────────────────────────────────────────────────────────
# 섹터별 기본 Fwd PER 중앙값 (실 데이터 연동 전 fallback)
# ──────────────────────────────────────────────────────────────
SECTOR_MEDIAN_FWD_PER: dict[str, float] = {
    "Industrials": 16.8,
    "Financials": 12.5,
    "Health Care": 22.4,
    "Consumer Staples": 16.2,
    "Energy": 10.5,
    "Information Technology": 25.0,
    "Communication Services": 14.0,
    "Consumer Discretionary": 18.0,
    "Materials": 14.5,
    "Utilities": 15.5,
    "Real Estate": 20.0,
}

_NA = {"value": None, "status": "NOT_APPLICABLE"}
_UNAVAIL = {"value": None, "status": "UNAVAILABLE"}


def _dv(value: float | None, status: str = "CONFIRMED") -> dict:
    return {"value": value, "status": status if value is not None else "UNAVAILABLE"}


def compute_valuation(snapshot: dict) -> dict:
    """
    Valuation dict 반환 (StockReport.valuation 계약 준수).

    snapshot이 완전한 StockReport JSON이면 그대로 사용.
    미완성 snapshot이면 가용 필드로 최소 구성.
    """
    if "valuation" in snapshot:
        return snapshot["valuation"]

    return _compute_from_minimal(snapshot)


def _compute_from_minimal(snap: dict) -> dict:
    """최소 스냅샷 필드에서 밸류에이션 구성 (real provider 연동 전 scaffold)."""
    sector = snap.get("sector", "")
    fwd_per = snap.get("fwd_per")
    trailing_per = snap.get("trailing_per")
    ev_ebitda = snap.get("ev_ebitda")
    pb = snap.get("pb")
    ps = snap.get("ps")
    p_fcf = snap.get("p_fcf")

    # 기본 지표는 Fwd PER
    primary = "Fwd PER"
    if sector == "Financials" and pb is not None:
        primary = "P/B"
    elif sector == "Energy" and ev_ebitda is not None:
        primary = "EV/EBITDA"

    sector_median = SECTOR_MEDIAN_FWD_PER.get(sector, 16.0)
    stock_primary = fwd_per if primary == "Fwd PER" else (pb if primary == "P/B" else ev_ebitda)

    if stock_primary and sector_median:
        discount_pct = round((sector_median - stock_primary) / sector_median * 100, 1)
        discount_status = "CONFIRMED"
    else:
        discount_pct = None
        discount_status = "UNAVAILABLE"

    # 금융섹터는 EV/EBITDA, P/FCF N/A
    if sector == "Financials":
        ev_ebitda_dv = _NA
        p_fcf_dv = _NA
    else:
        ev_ebitda_dv = _dv(ev_ebitda)
        p_fcf_dv = _dv(p_fcf)

    return {
        "primary_metric": primary,
        "metrics": {
            "fwd_per": _dv(fwd_per),
            "trailing_per": _dv(trailing_per),
            "ev_ebitda": ev_ebitda_dv,
            "pb": _dv(pb),
            "ps": _dv(ps),
            "p_fcf": p_fcf_dv,
        },
        "valuation_discount_vs_sector": {
            "status": discount_status,
            "metric_used": primary,
            "stock_value": stock_primary,
            "sector_median_value": sector_median,
            "discount_pct": discount_pct,
            "sector_comparison_name": f"{sector} Sector Peers",
            "comparison_universe_count": 20,
        },
        "historical_valuation_position": {
            "status": "UNVERIFIED",
            "metric_used": primary,
            "current_value": stock_primary,
            "three_year_mean": None,
            "three_year_min": None,
            "three_year_max": None,
            "percentile_rank": None,
        },
    }
