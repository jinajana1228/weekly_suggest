"""복합 스코어 계산 — 저평가 매력도 0~100점"""


def compute_composite_score(candidate: dict) -> float:
    """
    저평가 매력도 복합 스코어 (0–100).

    구성:
      discount_score      (최대 40점): 섹터 대비 할인율이 클수록 높은 점수
      catalyst_score      (최대 30점): 리레이팅 촉매 충족 비율
      risk_penalty        (최대 20점): 낮은 리스크 = 높은 점수
      drawdown_score      (최대 10점): 52주 고점 대비 낙폭이 클수록 높은 점수

    Note:
      에너지·원자재 등 고리스크 섹터는 risk_penalty로 자동 조정됨.
    """
    # ── 1. 섹터 할인 점수 ────────────────────────────────────────
    discount_pct = candidate.get("sector_discount_pct", 0.0)
    discount_score = min(40.0, discount_pct * 1.15)   # 35% 할인 → ~40점

    # ── 2. 촉매 점수 ────────────────────────────────────────────
    met = candidate.get("catalyst_met_count", 0)
    catalyst_score = (met / 3.0) * 30.0               # 3/3 충족 → 30점

    # ── 3. 리스크 점수 ──────────────────────────────────────────
    risk_map = {"LOW": 20.0, "MEDIUM": 12.0, "HIGH": 4.0, "UNASSESSED": 8.0}
    risk_score = risk_map.get(candidate.get("risk_level_max", "UNASSESSED"), 8.0)

    # ── 4. 가격 위치 점수 ────────────────────────────────────────
    pos_pct = candidate.get("week_52_position_pct", 50.0)
    drawdown_score = max(0.0, (1.0 - pos_pct / 100.0) * 10.0)

    total = discount_score + catalyst_score + risk_score + drawdown_score
    return round(min(100.0, total), 1)


def rank_candidates(passed: list[dict], top_n: int = 5) -> tuple[list[dict], list[dict]]:
    """
    점수 계산 후 상위 top_n 개를 선정.

    Returns:
        (selected, unselected)  각 항목에 score 필드 포함
    """
    scored = []
    for c in passed:
        scored.append({**c, "score": compute_composite_score(c)})

    scored.sort(key=lambda x: x["score"], reverse=True)

    selected = scored[:top_n]
    unselected = scored[top_n:]
    for u in unselected:
        u["exclusion_reason"] = "insufficient_composite_score"

    return selected, unselected
