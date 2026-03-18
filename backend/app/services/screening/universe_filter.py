"""유니버스 필터 — 기본 요건 미달 종목 제거"""
from typing import Any

# ────────────────────────────────────────────────────────────────
# Mock 유니버스 (VOL.3 기준 12개 후보)
#
# 추가 필드 (버킷 A/B 스코어링 전용):
#   revenue_growth_yoy_pct  : 전년대비 매출 성장률 (%)
#   eps_revision_trend      : EPS 개정 방향 (UP / STABLE / DOWN)
#   operating_margin_pct    : 영업이익률 (%)
#   roe_pct                 : 자기자본이익률 (%)
#   price_1m_change_pct     : 1개월 주가 변화율 (%)
#   price_3m_change_pct     : 3개월 주가 변화율 (%)
#   drawdown_from_52w_high_pct : 52주 고점 대비 낙폭 (%)
#   sector_tailwind_hint    : 섹터/업종 수혜 강도 (0.0–1.0)
#                             AI/반도체=0.9, 전력인프라=0.7, 금융성장=0.6,
#                             물류=0.4, 소비재=0.3
#   historical_pct_rank     : 3년 밸류에이션 백분위 (낮을수록 역사적으로 저렴)
#   market_growth_hint      : 시장·산업 구조 성장 여지 (0.0–1.0) [버킷 A 전용]
#                             실데이터 전환 시 LLM 분류 또는 업종 성장률 지표로 대체
#   policy_tailwind_hint    : 정책·규제 방향성 우호도 (0.0–1.0) [버킷 A 전용]
#                             AI인프라·에너지전환=0.8+, 금융=0.5~0.6, 소비재=0.2~0.3
# ────────────────────────────────────────────────────────────────
MOCK_UNIVERSE: list[dict[str, Any]] = [
    # ── 필터 통과 + 버킷 A 선발 (3) ─────────────────────────────
    {
        # VCNX: IT/반도체 — AI 수요 직접 수혜, 최고 성장률, EPS 상향
        "ticker": "VCNX", "company_name": "VectoNex Semiconductors Inc.",
        "sector": "Information Technology", "industry": "Semiconductors",
        "market_cap_usd_b": 11.4, "avg_daily_volume_m": 2.3,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 76.3, "week_52_high": 88.0, "week_52_low": 58.0,
        "week_52_position_pct": 15.7,
        # 스코어링 확장 필드
        "revenue_growth_yoy_pct": 22.4, "eps_revision_trend": "UP",
        "operating_margin_pct": 22.1, "roe_pct": 28.6,
        "price_1m_change_pct": -14.2, "price_3m_change_pct": -31.8,
        "drawdown_from_52w_high_pct": -35.6,
        "sector_tailwind_hint": 0.9,   # AI 반도체 수요 급증 — 최고 업종 tailwind
        "market_growth_hint": 0.95,   # AI 반도체 시장 구조적 성장 — 최고 수준
        "policy_tailwind_hint": 0.85, # AI 인프라 투자 정책 지원 강함
        "historical_pct_rank": 9,      # 3년 밸류에이션 역대 9분위 → 역사적 저점
        "sector_discount_pct": 29.1, "catalyst_met_count": 3, "risk_level_max": "HIGH",
    },
    {
        # BLFN: 금융/자산운용 — AUM 급증, EPS 상향, 저리스크 성장
        "ticker": "BLFN", "company_name": "Bluefin Capital Holdings",
        "sector": "Financials", "industry": "Asset Management",
        "market_cap_usd_b": 7.2, "avg_daily_volume_m": 1.4,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 52.8, "week_52_high": 71.4, "week_52_low": 46.0,
        "week_52_position_pct": 19.7,
        "revenue_growth_yoy_pct": 14.2, "eps_revision_trend": "UP",
        "operating_margin_pct": 32.4, "roe_pct": 22.4,
        "price_1m_change_pct": -6.3, "price_3m_change_pct": -19.4,
        "drawdown_from_52w_high_pct": -26.0,
        "sector_tailwind_hint": 0.6,   # 금리 사이클 전환 수혜, AUM 성장
        "market_growth_hint": 0.65,   # 대체투자·자산운용 업종 구조적 성장
        "policy_tailwind_hint": 0.55, # 금융 규제 완화 기조 — 중립~우호
        "historical_pct_rank": 16,
        "sector_discount_pct": 24.3, "catalyst_met_count": 2, "risk_level_max": "LOW",
    },
    {
        # NXPW: 에너지/독립발전 — 전력인프라 정책 수혜, 촉매 3/3 충족
        "ticker": "NXPW", "company_name": "NexaPower Energy Corp.",
        "sector": "Energy", "industry": "Independent Power Producers",
        "market_cap_usd_b": 5.6, "avg_daily_volume_m": 1.2,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 34.2, "week_52_high": 54.6, "week_52_low": 31.0,
        "week_52_position_pct": 12.2,
        "revenue_growth_yoy_pct": 8.4, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 18.5, "roe_pct": 11.3,
        "price_1m_change_pct": -9.1, "price_3m_change_pct": -28.3,
        "drawdown_from_52w_high_pct": -37.4,
        "sector_tailwind_hint": 0.7,   # 에너지 전환·전력 인프라 투자 확대 수혜
        "market_growth_hint": 0.80,   # 재생에너지·독립발전 시장 구조적 확대
        "policy_tailwind_hint": 0.75, # 청정에너지 정책·IRA 세제 혜택 강한 지원
        "historical_pct_rank": 11,
        "sector_discount_pct": 36.2, "catalyst_met_count": 3, "risk_level_max": "MEDIUM",
    },
    # ── 필터 통과 + 버킷 B 선발 (2) ─────────────────────────────
    {
        # STRL: 소비재/전문소매 — 낙폭 과대, 밸류에이션 회복 기대
        "ticker": "STRL", "company_name": "Streamline Retail Group Inc.",
        "sector": "Consumer Discretionary", "industry": "Specialty Retail",
        "market_cap_usd_b": 3.9, "avg_daily_volume_m": 0.8,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 28.45, "week_52_high": 41.2, "week_52_low": 25.0,
        "week_52_position_pct": 17.0,
        "revenue_growth_yoy_pct": 3.2, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 5.9, "roe_pct": 16.8,
        "price_1m_change_pct": -11.2, "price_3m_change_pct": -24.6,
        "drawdown_from_52w_high_pct": -30.9,
        "sector_tailwind_hint": 0.3,
        "market_growth_hint": 0.30,   # 전문소매 성장 여지 제한적 — 전자상거래 경쟁 심화
        "policy_tailwind_hint": 0.25, # 소비재 정책 지원 미미
        "historical_pct_rank": 19,
        "sector_discount_pct": 27.8, "catalyst_met_count": 2, "risk_level_max": "MEDIUM",
    },
    {
        # DFTL: 산업재/항공화물물류 — 공급망 정상화 기대, 안정 펀더멘털
        "ticker": "DFTL", "company_name": "Deltaflow Logistics Corp.",
        "sector": "Industrials", "industry": "Air Freight & Logistics",
        "market_cap_usd_b": 6.1, "avg_daily_volume_m": 1.1,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 43.1, "week_52_high": 58.5, "week_52_low": 38.0,
        "week_52_position_pct": 20.3,
        "revenue_growth_yoy_pct": 5.8, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 8.5, "roe_pct": 17.2,
        "price_1m_change_pct": -7.8, "price_3m_change_pct": -21.4,
        "drawdown_from_52w_high_pct": -26.2,
        "sector_tailwind_hint": 0.4,
        "market_growth_hint": 0.45,   # 물류·공급망 회복 기대 — 구조적 성장 제한
        "policy_tailwind_hint": 0.40, # 인프라 투자 정책 간접 수혜
        "historical_pct_rank": 14,
        "sector_discount_pct": 22.1, "catalyst_met_count": 2, "risk_level_max": "MEDIUM",
    },
    # ── 필터 통과 + 점수 미달 (2) ───────────────────────────────
    {
        "ticker": "NXST", "company_name": "Nexstar Broadcast Holdings",
        "sector": "Communication Services", "industry": "Broadcasting",
        "market_cap_usd_b": 3.2, "avg_daily_volume_m": 0.5,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 148.40, "week_52_high": 180.00, "week_52_low": 130.20,
        "week_52_position_pct": 40.1,
        "revenue_growth_yoy_pct": 1.8, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 14.2, "roe_pct": 9.4,
        "price_1m_change_pct": -2.1, "price_3m_change_pct": -8.4,
        "drawdown_from_52w_high_pct": -17.6,
        "sector_tailwind_hint": 0.2,
        "market_growth_hint": 0.20,   # 방송·미디어 구조 성장 부재 — 디지털 전환 역풍
        "policy_tailwind_hint": 0.20, # 미디어 규제 불확실, 정책 지원 없음
        "historical_pct_rank": 42,
        "sector_discount_pct": 11.2, "catalyst_met_count": 1, "risk_level_max": "MEDIUM",
    },
    {
        "ticker": "ATHN", "company_name": "Atheneum Technology Corp.",
        "sector": "Information Technology", "industry": "IT Consulting & Services",
        "market_cap_usd_b": 2.4, "avg_daily_volume_m": 0.4,
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 22.10, "week_52_high": 34.80, "week_52_low": 20.50,
        "week_52_position_pct": 38.5,
        "revenue_growth_yoy_pct": 4.1, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 9.8, "roe_pct": 12.3,
        "price_1m_change_pct": -3.4, "price_3m_change_pct": -9.2,
        "drawdown_from_52w_high_pct": -36.5,
        "sector_tailwind_hint": 0.35,
        "market_growth_hint": 0.45,   # IT컨설팅 AI 전환 수요 일부 수혜 — 제한적
        "policy_tailwind_hint": 0.35, # 기업 디지털화 정책 간접 수혜
        "historical_pct_rank": 38,
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
        "revenue_growth_yoy_pct": 6.2, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 11.4, "roe_pct": 14.1,
        "price_1m_change_pct": -4.8, "price_3m_change_pct": -12.3,
        "drawdown_from_52w_high_pct": -33.9,
        "sector_tailwind_hint": 0.4,
        "market_growth_hint": 0.35,   # 전기기기 업종 안정적이나 구조 성장 제한
        "policy_tailwind_hint": 0.30, # 인프라 정책 간접 수혜 — 미미
        "historical_pct_rank": 28,
        "sector_discount_pct": 22.0, "catalyst_met_count": 2, "risk_level_max": "LOW",
    },
    {
        "ticker": "MTRX", "company_name": "Matrix Energy Resources",
        "sector": "Energy", "industry": "Oil & Gas Equipment",
        "market_cap_usd_b": 2.3, "avg_daily_volume_m": 0.08,  # ← 거래량 미달
        "has_operating_income": True, "is_adr": False, "in_bankruptcy": False,
        "current_price": 11.20, "week_52_high": 19.50, "week_52_low": 9.80,
        "week_52_position_pct": 20.3,
        "revenue_growth_yoy_pct": 2.1, "eps_revision_trend": "DOWN",
        "operating_margin_pct": 7.2, "roe_pct": 6.8,
        "price_1m_change_pct": -8.4, "price_3m_change_pct": -22.1,
        "drawdown_from_52w_high_pct": -42.6,
        "sector_tailwind_hint": 0.35,
        "market_growth_hint": 0.25,   # 전통 석유가스 장비 — 에너지 전환으로 구조적 축소
        "policy_tailwind_hint": 0.20, # 탄소중립 정책 역풍
        "historical_pct_rank": 22,
        "sector_discount_pct": 30.1, "catalyst_met_count": 2, "risk_level_max": "HIGH",
    },
    {
        "ticker": "BCRX", "company_name": "BioCryst Pharmaceuticals",
        "sector": "Health Care", "industry": "Biotechnology",
        "market_cap_usd_b": 3.5, "avg_daily_volume_m": 2.1,
        "has_operating_income": False, "is_adr": False, "in_bankruptcy": False,  # ← 적자
        "current_price": 9.40, "week_52_high": 18.20, "week_52_low": 7.60,
        "week_52_position_pct": 22.0,
        "revenue_growth_yoy_pct": -5.2, "eps_revision_trend": "DOWN",
        "operating_margin_pct": -8.4, "roe_pct": -12.1,
        "price_1m_change_pct": -18.3, "price_3m_change_pct": -41.2,
        "drawdown_from_52w_high_pct": -48.4,
        "sector_tailwind_hint": 0.25,
        "market_growth_hint": 0.40,   # 바이오테크 시장 성장 있으나 임상 불확실성 높음
        "policy_tailwind_hint": 0.30, # FDA 규제 긍정·부정 혼재
        "historical_pct_rank": 35,
        "sector_discount_pct": 35.0, "catalyst_met_count": 1, "risk_level_max": "HIGH",
    },
    {
        "ticker": "LVMUY", "company_name": "LVMH Moët Hennessy (ADR)",
        "sector": "Consumer Discretionary", "industry": "Personal Luxury Goods",
        "market_cap_usd_b": 12.0, "avg_daily_volume_m": 0.6,
        "has_operating_income": True, "is_adr": True, "in_bankruptcy": False,  # ← ADR
        "current_price": 132.80, "week_52_high": 165.00, "week_52_low": 110.50,
        "week_52_position_pct": 41.6,
        "revenue_growth_yoy_pct": 3.8, "eps_revision_trend": "STABLE",
        "operating_margin_pct": 21.3, "roe_pct": 18.6,
        "price_1m_change_pct": -1.2, "price_3m_change_pct": -6.8,
        "drawdown_from_52w_high_pct": -19.5,
        "sector_tailwind_hint": 0.3,
        "market_growth_hint": 0.30,   # 명품 소비재 성장 있으나 경기 민감 — 중국 둔화 역풍
        "policy_tailwind_hint": 0.20, # ADR 정책 불리, 관세 리스크
        "historical_pct_rank": 45,
        "sector_discount_pct": 15.2, "catalyst_met_count": 1, "risk_level_max": "LOW",
    },
    {
        "ticker": "CLNE", "company_name": "Clean Energy Fuels Corp.",
        "sector": "Energy", "industry": "Gas Utilities",
        "market_cap_usd_b": 0.8, "avg_daily_volume_m": 1.2,
        "has_operating_income": False, "is_adr": False, "in_bankruptcy": True,  # ← 부도 위험
        "current_price": 3.10, "week_52_high": 7.80, "week_52_low": 2.40,
        "week_52_position_pct": 10.0,
        "revenue_growth_yoy_pct": -18.4, "eps_revision_trend": "DOWN",
        "operating_margin_pct": -22.1, "roe_pct": -38.4,
        "price_1m_change_pct": -22.4, "price_3m_change_pct": -54.8,
        "drawdown_from_52w_high_pct": -60.3,
        "sector_tailwind_hint": 0.2,
        "market_growth_hint": 0.30,   # 청정연료 시장 성장 있으나 부도 위험 — 실질 무의미
        "policy_tailwind_hint": 0.35, # 청정에너지 정책 수혜 가능하나 재무 위기 우선
        "historical_pct_rank": 60,
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
