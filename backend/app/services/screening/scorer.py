"""복합 스코어 계산 — 버킷 A (성장 추세 3개) + 버킷 B (저평가 2개) 2-버킷 선발"""


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


# ── 버킷 A: 성장 추세 스코어 ──────────────────────────────────────

def compute_growth_trajectory_score(c: dict) -> float:
    """
    버킷 A — 성장 추세 종목 스코어 (0–100).

    정의:
      "현재도 성장 중이고, 시장 성장성·정책 방향성까지 고려할 때
       앞으로도 성장 여지가 남아 있는 종목"

    구성 및 가중치:
      growth_trend_score      (×0.35): 현재 성장 추세
        - revenue_growth_yoy_pct  (40%): 매출 성장률
        - eps_revision_trend       (30%): EPS 개정 방향 (UP/STABLE/DOWN)
        - operating_margin_pct     (15%): 수익성 훼손 없음 확인
        - roe_pct                  (15%): 자본 효율성
      market_expansion_score  (×0.20): 시장·산업 구조 성장 여지 (market_growth_hint)
      policy_alignment_score  (×0.15): 정책·규제 방향성 우호도 (policy_tailwind_hint)
      upside_remaining_score  (×0.15): 추가 상승 여지 (과열 아님 확인)
        - 기저: 1 - week_52_position_pct/100 (52주 하단에 가까울수록 여지 큼)
        - 과열 감점: sector_discount_pct < -30 이면 프리미엄 강도에 비례해 최대 50% 감점
      catalyst_score          (×0.10): 리레이팅 트리거 존재 여부
      risk_penalty            (×0.20 차감)

    설계 원칙:
    - market_growth_hint / policy_tailwind_hint: MOCK_UNIVERSE에서 섹터·업종별로
      0.0–1.0 직접 설정. 실데이터 모드에서는 LLM 분류 또는 업종 분류표로 대체 가능.
    - 단순 모멘텀(주가 상승)은 upside_remaining에서 간접 반영.
      과거 모멘텀 점수가 성장 추세 기준을 왜곡하지 않도록 별도 모멘텀 가중치 제거.
    - 과열 종목(섹터 대비 30% 이상 프리미엄) 자동 감점.
    """
    # 1) growth_trend_score: 현재 성장 추세
    rev_growth = max(0.0, c.get("revenue_growth_yoy_pct", 0.0))
    rev_norm = min(1.0, rev_growth / 25.0)           # 25% 이상 → 만점

    eps_rev_norm = _eps_revision_score(c.get("eps_revision_trend", "STABLE"))

    op_margin = max(0.0, c.get("operating_margin_pct", 0.0))
    op_norm = min(1.0, op_margin / 35.0)              # 35% 마진 → 만점

    roe = max(0.0, c.get("roe_pct", 0.0))
    roe_norm = min(1.0, roe / 30.0)                   # ROE 30% → 만점

    growth_trend_score = (
        0.40 * rev_norm
        + 0.30 * eps_rev_norm
        + 0.15 * op_norm
        + 0.15 * roe_norm
    )

    # 2) market_expansion_score: 시장·산업 구조 성장 여지
    market_expansion_score = float(c.get("market_growth_hint", 0.5))

    # 3) policy_alignment_score: 정책·규제 방향성 우호도
    policy_alignment_score = float(c.get("policy_tailwind_hint", 0.5))

    # 4) upside_remaining_score: 추가 상승 여지 (과열 감점 포함)
    w52 = c.get("week_52_position_pct", 50.0)
    upside_base = max(0.0, 1.0 - w52 / 100.0)

    discount = c.get("sector_discount_pct", 0.0)
    if discount < -30.0:
        # 섹터 대비 30% 이상 프리미엄 → 과열 감점 (최대 50% 감점)
        premium_excess = min(1.0, (-discount - 30.0) / 30.0)
        upside_remaining_score = upside_base * (1.0 - 0.5 * premium_excess)
    else:
        upside_remaining_score = upside_base

    # 5) catalyst_score: 리레이팅 트리거
    met = c.get("catalyst_met_count", 0)
    catalyst_score = min(1.0, met / 3.0)

    raw = (
        0.35 * growth_trend_score
        + 0.20 * market_expansion_score
        + 0.15 * policy_alignment_score
        + 0.15 * upside_remaining_score
        + 0.10 * catalyst_score
        - 0.20 * _risk_penalty(c)
    )
    return round(max(0.0, min(1.0, raw)) * 100, 1)


# ── 하위 호환 래퍼 ────────────────────────────────────────────────

def compute_growth_beneficiary_score(c: dict) -> float:
    """하위 호환 래퍼 — compute_growth_trajectory_score 위임."""
    return compute_growth_trajectory_score(c)


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
    - 버킷 B 최소 조건(sector_discount_pct>=10%, catalyst>=1)은
      bucket_select_candidates()에서 별도 적용
    """
    # 1) sector_discount_score
    discount = max(0.0, c.get("sector_discount_pct", 0.0))
    discount_score = min(1.0, discount / 40.0)            # 40% 할인 → 만점

    # 2) historical_cheapness_score: 역사적 백분위 (낮을수록 저렴 → 높은 점수)
    hist_rank = c.get("historical_pct_rank", 50.0)         # 0~100
    hist_score = max(0.0, min(1.0, 1.0 - hist_rank / 100.0))

    # 3) catalyst_score: 1개 이상 충족 시 value trap 아닐 가능성 높음
    met = c.get("catalyst_met_count", 0)
    catalyst_score = min(1.0, met / 3.0)

    # 4) drawdown_score: oversold 강도 (더 많이 빠진 종목 = 반등 여지)
    drawdown = abs(c.get("drawdown_from_52w_high_pct", 0.0))
    drawdown_score = min(1.0, drawdown / 50.0)             # 50% 낙폭 → 만점

    # 5) financial_quality_score: 수익성 기반 재무 훼손 여부 확인
    op_margin = max(0.0, c.get("operating_margin_pct", 0.0))
    quality_score = min(1.0, op_margin / 20.0)             # 20% 마진 → 만점

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


# ── 섹터 분산 선발 헬퍼 ──────────────────────────────────────────

def _select_with_sector_diversity(
    sorted_candidates: list[dict],
    count: int,
) -> list[dict]:
    """
    섹터 분산을 고려한 상위 N개 선발.

    동일 섹터에서 최대 1개만 선발 (가능한 한).
    충분한 다양성 확보가 어려운 경우 (전체 후보 섹터 수 부족) 점수순으로 보충.
    """
    selected: list[dict] = []
    used_sectors: list[str] = []
    overflow: list[dict] = []  # 점수 우수하나 섹터 중복으로 대기

    for candidate in sorted_candidates:
        sector = candidate.get("sector", "Unknown")
        if sector not in used_sectors:
            selected.append(candidate)
            used_sectors.append(sector)
            if len(selected) == count:
                break
        else:
            overflow.append(candidate)

    # 다양한 섹터로 count를 채우지 못한 경우 overflow에서 보충 (점수순)
    if len(selected) < count:
        selected_tickers = {s["ticker"] for s in selected}
        for candidate in overflow:
            if candidate["ticker"] not in selected_tickers:
                selected.append(candidate)
                if len(selected) == count:
                    break

    return selected


# ── 2-버킷 선발 ──────────────────────────────────────────────────

def bucket_select_candidates(
    passed: list[dict],
    bucket_a_count: int = 3,
    bucket_b_count: int = 2,
) -> tuple[list[dict], list[dict]]:
    """
    버킷 A (성장 추세) + 버킷 B (저평가) 2-버킷 선발.

    흐름:
      1. 모든 후보에 버킷 A/B 스코어 동시 계산
      2. 버킷 A: 스코어 상위 후보 중 섹터 분산 고려해 bucket_a_count 개 선발
         → selection_type = GROWTH_TRAJECTORY
      3. 나머지 후보 중 버킷 B 최소 조건 충족 + 스코어 상위 bucket_b_count 개 선발
         → selection_type = UNDERVALUED

    버킷 A 섹터 분산:
      - 동일 섹터에서 최대 1개 선발 (가능한 한)
      - 후보 부족 시 점수순으로 충원

    버킷 B 최소 조건:
      - sector_discount_pct >= 10%  (value trap 방어)
      - catalyst_met_count >= 1     (리레이팅 근거 존재)
    """
    # A/B 스코어 동시 계산
    scored = []
    for c in passed:
        scored.append({
            **c,
            "score_a": compute_growth_trajectory_score(c),
            "score_b": compute_undervalued_score(c),
        })

    # 버킷 A: 성장 추세 — 섹터 분산 고려 선발
    sorted_a = sorted(scored, key=lambda x: x["score_a"], reverse=True)
    selected_a = _select_with_sector_diversity(sorted_a, bucket_a_count)
    selected_a_tickers = {s["ticker"] for s in selected_a}

    for s in selected_a:
        s["selection_type"] = "GROWTH_TRAJECTORY"
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
