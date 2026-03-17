"""유니버스 필터 — 기본 요건 미달 종목 제거"""
from typing import Any

# ────────────────────────────────────────────────────────────────
# Mock 유니버스 (12개 후보)
# ────────────────────────────────────────────────────────────────
MOCK_UNIVERSE: list[dict[str, Any]] = [
    # ── 필터 통과 + 최종 선정 (5) ──────────────────────────────
    {
        "ticker": "MFGI", "company_name": "Meridian Fastening Group Inc.",
        "sector": "Industrials", "industry": "Industrial Machinery",
        "market_cap_usd_b": 4.8, "avg_daily_volume_m": 1.8,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 41.25, "week_52_high": 67.80, "week_52_low": 38.10,
        "week_52_position_pct": 10.9,
        "sector_discount_pct": 33.3, "catalyst_met_count": 3, "risk_level_max": "LOW",
    },
    {
        "ticker": "RVNC", "company_name": "Ravencroft Bancorp Inc.",
        "sector": "Financials", "industry": "Regional Banks",
        "market_cap_usd_b": 4.2, "avg_daily_volume_m": 0.9,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 28.75, "week_52_high": 41.20, "week_52_low": 25.30,
        "week_52_position_pct": 21.9,
        "sector_discount_pct": 27.8, "catalyst_met_count": 2, "risk_level_max": "MEDIUM",
    },
    {
        "ticker": "HLTH", "company_name": "HealthCore Systems Corp.",
        "sector": "Health Care", "industry": "Health Care Services",
        "market_cap_usd_b": 6.8, "avg_daily_volume_m": 1.1,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 54.20, "week_52_high": 82.30, "week_52_low": 49.10,
        "week_52_position_pct": 15.4,
        "sector_discount_pct": 22.8, "catalyst_met_count": 2, "risk_level_max": "MEDIUM",
    },
    {
        "ticker": "CSTM", "company_name": "Creston Consumer Brands Ltd.",
        "sector": "Consumer Staples", "industry": "Packaged Foods & Meats",
        "market_cap_usd_b": 5.1, "avg_daily_volume_m": 0.7,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 33.60, "week_52_high": 50.20, "week_52_low": 30.40,
        "week_52_position_pct": 16.5,
        "sector_discount_pct": 18.5, "catalyst_met_count": 2, "risk_level_max": "LOW",
    },
    {
        "ticker": "ENXT", "company_name": "EnerNext Resources Corp.",
        "sector": "Energy", "industry": "Oil & Gas E&P",
        "market_cap_usd_b": 3.8, "avg_daily_volume_m": 1.5,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 19.85, "week_52_high": 34.60, "week_52_low": 17.20,
        "week_52_position_pct": 15.1,
        "sector_discount_pct": 41.4, "catalyst_met_count": 3, "risk_level_max": "HIGH",
    },
    # ── 필터 통과 + 점수 미달 (2) ───────────────────────────────
    {
        "ticker": "NXST", "company_name": "Nexstar Broadcast Holdings",
        "sector": "Communication Services", "industry": "Broadcasting",
        "market_cap_usd_b": 3.2, "avg_daily_volume_m": 0.5,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 148.40, "week_52_high": 180.00, "week_52_low": 130.20,
        "week_52_position_pct": 40.1,
        "sector_discount_pct": 11.2, "catalyst_met_count": 1, "risk_level_max": "MEDIUM",
    },
    {
        "ticker": "ATHN", "company_name": "Atheneum Technology Corp.",
        "sector": "Information Technology", "industry": "IT Consulting & Services",
        "market_cap_usd_b": 2.4, "avg_daily_volume_m": 0.4,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 22.10, "week_52_high": 34.80, "week_52_low": 20.50,
        "week_52_position_pct": 38.5,
        "sector_discount_pct": 14.6, "catalyst_met_count": 1, "risk_level_max": "MEDIUM",
    },
    # ── 필터 제외 (5) ───────────────────────────────────────────
    {
        "ticker": "PLXS", "company_name": "Plexis Industrial Systems Inc.",
        "sector": "Industrials", "industry": "Electrical Equipment",
        "market_cap_usd_b": 1.1, "avg_daily_volume_m": 0.3,   # ← 시총 미달
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 18.50, "week_52_high": 28.00, "week_52_low": 15.20,
        "week_52_position_pct": 31.6,
        "sector_discount_pct": 22.0, "catalyst_met_count": 2, "risk_level_max": "LOW",
    },
    {
        "ticker": "MTRX", "company_name": "Matrix Energy Resources",
        "sector": "Energy", "industry": "Oil & Gas Equipment",
        "market_cap_usd_b": 2.3, "avg_daily_volume_m": 0.08,  # ← 거래량 미달
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 11.20, "week_52_high": 19.50, "week_52_low": 9.80,
        "week_52_position_pct": 20.3,
        "sector_discount_pct": 30.1, "catalyst_met_count": 2, "risk_level_max": "HIGH",
    },
    {
        "ticker": "BCRX", "company_name": "BioCryst Pharmaceuticals",
        "sector": "Health Care", "industry": "Biotechnology",
        "market_cap_usd_b": 3.5, "avg_daily_volume_m": 2.1,
        "has_operating_income": False, "is_adr": False, "in_bankruptcy": False,  # ← 적자
        "current_price": 9.40, "week_52_high": 18.20, "week_52_low": 7.60,
        "week_52_position_pct": 22.0,
        "sector_discount_pct": 35.0, "catalyst_met_count": 1, "risk_level_max": "HIGH",
    },
    {
        "ticker": "LVMUY", "company_name": "LVMH Moët Hennessy (ADR)",
        "sector": "Consumer Discretionary", "industry": "Personal Luxury Goods",
        "market_cap_usd_b": 12.0, "avg_daily_volume_m": 0.6,
        "has_operating_income": True, "is_adr": True, "in_bankruptcy": False,  # ← ADR
        "current_price": 132.80, "week_52_high": 165.00, "week_52_low": 110.50,
        "week_52_position_pct": 41.6,
        "sector_discount_pct": 15.2, "catalyst_met_count": 1, "risk_level_max": "LOW",
    },
    {
        "ticker": "CLNE", "company_name": "Clean Energy Fuels Corp.",
        "sector": "Energy", "industry": "Gas Utilities",
        "market_cap_usd_b": 0.8, "avg_daily_volume_m": 1.2,
        "has_operating_income": False, "is_adr": False, "in_bankruptcy": True,  # ← 부도 위험
        "current_price": 3.10, "week_52_high": 7.80, "week_52_low": 2.40,
        "week_52_position_pct": 10.0,
        "sector_discount_pct": 55.0, "catalyst_met_count": 0, "risk_level_max": "HIGH",
    },
]


# ────────────────────────────────────────────────────────────────
# 기본 필터 기준값
# ────────────────────────────────────────────────────────────────
DEFAULT_FILTERS = {
    "min_market_cap_usd_b": 2.0,      # 시총 최소 $2B
    "min_avg_daily_volume_m": 0.1,    # 일평균 거래량 최소 100만 주
    "require_operating_income": True, # 영업이익 양수
    "exclude_adr": True,              # ADR 제외
    "exclude_bankruptcy": True,       # 부도 위험 제외
}


def apply_universe_filter(
    candidates: list[dict],
    filters: dict | None = None,
) -> tuple[list[dict], list[dict]]:
    """
    기본 요건 필터 적용.

    Returns:
        (passed, excluded)  각 항목에 exclusion_reason 필드 포함
    """
    f = {**DEFAULT_FILTERS, **(filters or {})}

    passed: list[dict] = []
    excluded: list[dict] = []

    for c in candidates:
        reason = _check_exclusion(c, f)
        item = {**c}
        if reason:
            item["exclusion_reason"] = reason
            excluded.append(item)
        else:
            passed.append(item)

    return passed, excluded


def _check_exclusion(c: dict, f: dict) -> str | None:
    if c.get("market_cap_usd_b", 0) < f["min_market_cap_usd_b"]:
        return f"market_cap_below_{f['min_market_cap_usd_b']}B"
    if c.get("avg_daily_volume_m", 0) < f["min_avg_daily_volume_m"]:
        return "avg_daily_volume_below_threshold"
    if f["require_operating_income"] and not c.get("has_operating_income", False):
        return "no_operating_income"
    if f["exclude_adr"] and c.get("is_adr", False):
        return "adr_excluded"
    if f["exclude_bankruptcy"] and c.get("in_bankruptcy", False):
        return "bankruptcy_risk"
    return None
