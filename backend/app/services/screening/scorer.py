"""복합 스코어 계산 — 버킷 A (성장/수혜 3개) + 버킷 B (저평가 2개) 2-버킷 선발"""


# ── 공통 헬퍼 ────────────────────────────────────────────────────

def _risk_penalty(candidate: dict) -> float:
    """
    리스크 레벨 → 패널티 (0.0–1.0).
    HIGH=0.8, MEDIUM=0.5, LOW=0.2, UNASSESSED=0.4
    """
    risk_map = {"LOW": 0.2, "MEDIUM": 0.5, "HIGH": 0.8, "UNASSESSED": 0.4}
    return risk_map.get(candidate.get("risk_level_max", "UNASSESSED"), 0.4)


def _eps_revision_score(trend: str) -> float:
    """EPS revision trend → 0.0–1.0"""
    mapping = {
        "UP": 1.0, "UPWARD": 1.0,
        "STABLE": 0.5,
        "DOWN": 0.0, "DOWNWARD": 0.0,
        "UNAVAILABLE": 0.3,
    }
    return mapping.get(str(trend).upper(), 0.3)


# ── 버킷 A: 성장/모멘텀/정책·산업 수혜 스코어 ──────────────────

def compute_growth_beneficiary_score(c: dict) -> float:
    """
    버킷 A 복합 스코어 (0–100).

    구성 및 가중치:
      growth_score            (×0.30): 매출 성장률 + EPS 개정 + 영업마진 + ROE
      momentum_score          (×0.25): 3M 주가 변화율 + 1M 주가 변화율 + 52주 위치
      earnings_revision_score (×0.20): EPS revision trend (UP/STABLE/DOWN)
      catalyst_score          (×0.15): 촉매 충족 비율 (met_count / 3)
      sector_tailwind_score   (×0.10): 섹터 수혜 강도 (sector_tailwind_hint 0–1)
      risk_penalty            (×0.20 차감): 리스크 레벨에 따른 감점

    설계 원칙:
    - 정책수혜는 직접 판별 대신 sector_tailwind_hint(업종 수혜 강도 proxy) +
      catalyst(실적/이벤트 근거) + earnings_revision(상향 여부) 조합으로 간접 판별
    - 모멘텀은 상대 서열 반영 (음수 환경에서도 덜 하락한 종목 우위)
    """
    # 1) growth_score: 성장성 지표 종합
    rev_growth = max(0.0, c.get("revenue_growth_yoy_pct", 0.0))
    rev_norm = min(1.0, rev_growth / 25.0)          # 25% 이상 → 만점

    eps_rev_norm = _eps_revision_score(c.get("eps_revision_trend", "STABLE"))

    op_margin = max(0.0, c.get("operating_margin_pct", 0.0))
    op_norm = min(1.0, op_margin / 35.0)             # 35% 마진 → 만점

    roe = max(0.0, c.get("roe_pct", 0.0))
    roe_norm = min(1.0, roe / 30.0)                  # ROE 30% → 만점

    growth_score = (
        0.40 * rev_norm
        + 0.30 * eps_rev_norm
        + 0.15 * op_norm
        + 0.15 * roe_norm
    )

    # 2) momentum_score: 상대 모멘텀 (기준선 -40%, +20% 구간 선형 변환)
    p3m = c.get("price_3m_change_pct", 0.0)
    p3m_norm = max(0.0, min(1.0, (p3m + 40.0) / 60.0))  # -40→0, 0→0.67, +20→1.0

    p1m = c.get("price_1m_change_pct", 0.0)
    p1m_norm = max(0.0, min(1.0, (p1m + 20.0) / 30.0))  # -20→0, 0→0.67, +10→1.0

    w52 = c.get("week_52_position_pct", 50.0)
    w52_norm = w52 / 100.0

    momentum_score = (
        0.40 * p3m_norm
        + 0.30 * p1m_norm
        + 0.30 * w52_norm
    )

    # 3) earnings_revision_score: EPS 상향 여부 (독립 가중)
    earnings_revision_score = _eps_revision_score(c.get("eps_revision_trend", "STABLE"))

    # 4) catalyst_score: 리레이팅 촉매 충족 비율
    met = c.get("catalyst_met_count", 0)
    catalyst_score = min(1.0, met / 3.0)

    # 5) sector_tailwind_score: 섹터/업종 수혜 강도 (0.0–1.0 직접 입력 또는 기본 0.5)
    sector_tailwind_score = float(c.get("sector_tailwind_hint", 0.5))

    raw = (
        0.30 * growth_score
        + 0.25 * momentum_score
        + 0.20 * earnings_revision_score
        + 0.15 * catalyst_score
        + 0.10 * sector_tailwind_score
        - 0.20 * _risk_penalty(c)
    )
    return round(max(0.0, min(1.0, raw)) * 100, 1)


# ── 버킷 B: 저평가 스코어 ────────────────────────────────────────

def compute_undervalued_score(c: dict) -> float:
    """
    버킷 B 복합 스코어 (0–100).

    구성 및 가중치:
      sector_discount_score       (×0.35): 섹터 중앙값 대비 할인율
      historical_cheapness_score  (×0.20): 3년 역사적 밸류에이션 백분위 (낮을수록 저렴)
      catalyst_score              (×0.20): 촉매 충족 비율 (value trap 방어)
      drawdown_score              (×0.15): 52주 고점 대비 낙폭 (oversold proxy)
      financial_quality_score     (×0.10): 영업마진 기반 수익성 확인
      risk_penalty                (×0.20 차감)

    설계 원칙:
    - 단순 할인율 외에 역사적 저렴함 + 촉매(value trap 방어)를 결합
    - 재무 훼손이 심하거나 촉매가 없는 경우 자동 감점
    """
    # 1) sector_discount_score
    discount = max(0.0, c.get("sector_discount_pct", 0.0))
    discount_score = min(1.0, discount / 40.0)           # 40% 할인 → 만점

    # 2) historical_cheapness_score: 역사적 백분위 (낮을수록 저렴 → 높은 점수)
    hist_rank = c.get("historical_pct_rank", 50.0)        # 0~100
    hist_score = max(0.0, min(1.0, 1.0 - hist_rank / 100.0))

    # 3) catalyst_score: 1개 이상 충족 시 value trap 아닐 가능성 높음
    met = c.get("catalyst_met_count", 0)
    catalyst_score = min(1.0, met / 3.0)

    # 4) drawdown_score: oversold 강도 (더 많이 빠진 종목 = 반등 여지)
    drawdown = abs(c.get("drawdown_from_52w_high_pct", 0.0))
    drawdown_score = min(1.0, drawdown / 50.0)            # 50% 낙폭 → 만점

    # 5) financial_quality_score: 수익성 기반 재무 훼손 여부 확인
    op_margin = max(0.0, c.get("operating_margin_pct", 0.0))
    quality_score = min(1.0, op_margin / 20.0)            # 20% 마진 → 만점

    raw = (
        0.35 * discount_score
        + 0.20 * hist_score
        + 0.20 * catalyst_score
        + 0.15 * drawdown_score
        + 0.10 * quality_score
        - 0.20 * _risk_penalty(c)
    )
    return round(max(0.0, min(1.0, raw)) * 100, 1)


# ── 구 API 호환 래퍼 ─────────────────────────────────────────────

def compute_composite_score(candidate: dict) -> float:
    """하위 호환 래퍼 — 저평가 스코어 반환 (단일 스코어 필요 시)."""
    return compute_undervalued_score(candidate)


# ── 2-버킷 선발 ──────────────────────────────────────────────────

def bucket_select_candidates(
    passed: list[dict],
    bucket_a_count: int = 3,
    bucket_b_count: int = 2,
) -> tuple[list[dict], list[dict]]:
    """
    버킷 A (성장/수혜) + 버킷 B (저평가) 2-버킷 선발.

    흐름:
      1. 모든 후보에 버킷 A/B 스코어 동시 계산
      2. 버킷 A 스코어 상위 bucket_a_count 개 선발
         → selection_type = GROWTH_BENEFICIARY
      3. 나머지 후보 중 버킷 B 최소 조건 충족 + 스코어 상위 bucket_b_count 개 선발
         → selection_type = UNDERVALUED

    버킷 B 최소 조건:
      - sector_discount_pct >= 10%  (value trap 아님)
      - catalyst_met_count >= 1     (리레이팅 근거 존재)
    """
    # A/B 스코어 동시 계산
    scored = []
    for c in passed:
        scored.append({
            **c,
            "score_a": compute_growth_beneficiary_score(c),
            "score_b": compute_undervalued_score(c),
        })

    # 버킷 A: 성장/수혜 상위 선발
    sorted_a = sorted(scored, key=lambda x: x["score_a"], reverse=True)
    selected_a = sorted_a[:bucket_a_count]
    selected_a_tickers = {s["ticker"] for s in selected_a}

    for s in selected_a:
        s["selection_type"] = "GROWTH_BENEFICIARY"
        s["score"] = s["score_a"]

    # 버킷 B: A 선발 제외 + 최소 조건 + 저평가 상위 선발
    remaining = [
        c for c in scored
        if c["ticker"] not in selected_a_tickers
        and c.get("sector_discount_pct", 0.0) >= 10.0
        and c.get("catalyst_met_count", 0) >= 1
    ]
    sorted_b = sorted(remaining, key=lambda x: x["score_b"], reverse=True)
    selected_b = sorted_b[:bucket_b_count]

    selected_b_tickers = {s["ticker"] for s in selected_b}
    for s in selected_b:
        s["selection_type"] = "UNDERVALUED"
        s["score"] = s["score_b"]

    # 미선발
    all_selected = selected_a_tickers | selected_b_tickers
    unselected = [
        {**c, "exclusion_reason": "insufficient_bucket_score"}
        for c in scored
        if c["ticker"] not in all_selected
    ]

    return selected_a + selected_b, unselected


def rank_candidates(passed: list[dict], top_n: int = 5) -> tuple[list[dict], list[dict]]:
    """
    기존 API 호환 진입점 — bucket_select_candidates 경유.

    top_n=5 → bucket_a=3, bucket_b=2 (고정 비율).
    """
    bucket_a = max(1, top_n - 2)
    bucket_b = top_n - bucket_a
    return bucket_select_candidates(passed, bucket_a_count=bucket_a, bucket_b_count=bucket_b)
