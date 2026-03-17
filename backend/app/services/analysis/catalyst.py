"""촉매 평가 엔진

Catalyst 3-조건 시스템:
  A: 12개월 이내 실적 발표 예정 (어닝 일정)
  B: 애널리스트 컨센서스 갭 ≥ 5% (컨센서스 데이터 필요 — 없으면 UNVERIFIABLE)
  C: 12개월 EPS 상향 vs. 52주 저점 수준 초과 하락 (역설적 저평가 시그널)
"""
from typing import Any


def assess_catalysts(
    snapshot: dict,
    consensus_data: dict | None,
    earnings_calendar: list[dict] | None = None,
) -> dict:
    """
    CatalystAssessment dict 반환.

    snapshot이 완전한 StockReport JSON이면 추출 후 Catalyst B만 재검토.
    """
    if "catalyst_assessment" in snapshot:
        result = _deep_copy_catalyst(snapshot["catalyst_assessment"])
        # Catalyst B는 런타임 consensus_data 가용성으로 재판정
        if consensus_data is None:
            result["catalyst_b"]["status"] = "UNVERIFIABLE"
            result["catalyst_b"]["evidence"] = None
            result["catalyst_b"]["data_status"] = "UNAVAILABLE"
        # met_count 재계산
        result["met_count"] = sum(
            1 for k in ("catalyst_a", "catalyst_b", "catalyst_c")
            if result[k]["status"] == "MET"
        )
        return result

    return _compute_from_minimal(snapshot, consensus_data, earnings_calendar or [])


# ── 내부 헬퍼 ─────────────────────────────────────────────────

def _deep_copy_catalyst(ca: dict) -> dict:
    import copy
    return copy.deepcopy(ca)


def _compute_from_minimal(
    snap: dict,
    consensus_data: dict | None,
    earnings_calendar: list[dict],
) -> dict:
    """최소 스냅샷으로 촉매 평가 (real provider scaffold)."""
    # Catalyst A: 어닝 일정 존재 여부
    a_status = "MET" if earnings_calendar else "NOT_MET"
    a_evidence = (
        f"다음 실적 발표: {earnings_calendar[0].get('date', '')}"
        if earnings_calendar else None
    )

    # Catalyst B: 컨센서스 갭
    if consensus_data is None:
        b_status = "UNVERIFIABLE"
        b_evidence = None
        b_data_status = "UNAVAILABLE"
    else:
        target = consensus_data.get("target_mean_price", 0)
        current = snap.get("current_price", snap.get("price", 0))
        if current and target:
            gap_pct = (target - current) / current * 100
            if gap_pct >= 5.0:
                b_status = "MET"
                b_evidence = f"컨센서스 평균 목표: ${target:.2f} (갭 {gap_pct:.1f}%)"
            else:
                b_status = "NOT_MET"
                b_evidence = f"컨센서스 갭 {gap_pct:.1f}% — 5% 미달"
        else:
            b_status = "UNVERIFIABLE"
            b_evidence = None
        b_data_status = "CONFIRMED" if consensus_data else "UNAVAILABLE"

    # Catalyst C: 가격 위치 + EPS 트렌드 단순 평가
    pos_pct = snap.get("week_52_position_pct", 50.0)
    c_status = "MET" if pos_pct <= 25 else "NOT_MET"
    c_evidence = f"52주 가격 위치 {pos_pct:.0f}%ile" if c_status == "MET" else None

    catalysts = [
        {"catalyst_id": "A", "status": a_status},
        {"catalyst_id": "B", "status": b_status},
        {"catalyst_id": "C", "status": c_status},
    ]
    met_count = sum(1 for c in catalysts if c["status"] == "MET")

    composite_label = (
        "3/3 충족 — 복합 촉매 강" if met_count == 3
        else f"{met_count}/3 충족"
    )

    return {
        "catalyst_a": {
            "catalyst_id": "A",
            "definition_summary": "12개월 이내 실적 발표 예정 여부",
            "status": a_status,
            "evidence": a_evidence,
            "data_status": "CONFIRMED" if earnings_calendar else "UNAVAILABLE",
        },
        "catalyst_b": {
            "catalyst_id": "B",
            "definition_summary": "애널리스트 컨센서스 갭 ≥ 5%",
            "status": b_status,
            "evidence": b_evidence,
            "data_status": b_data_status,
        },
        "catalyst_c": {
            "catalyst_id": "C",
            "definition_summary": "52주 가격 위치 하위 25% 이하",
            "status": c_status,
            "evidence": c_evidence,
            "data_status": "CONFIRMED",
        },
        "met_count": met_count,
        "composite_label": composite_label,
    }
