from fastapi import APIRouter, HTTPException, Query
from app.storage.file_store import file_store

router = APIRouter()

_EMPTY_CHART = {
    "price_series": [],
    "event_markers": [],
    "reference_lines": [],
    "interest_range_band": None,
}


def _transform_chart(raw: dict, period_days: int) -> dict:
    """
    Mock JSON 파일 포맷 → ChartDataPackage 프론트엔드 타입으로 변환.

    Mock 파일 키:
      data[]                   → price_series[]
      reference_lines[].label  → line_type (예: "WEEK_52_HIGH")
      event_markers[].description → detail
      interest_range_band.color_hint 제거, conditional_note 추가
    """
    # 1) price series (mock JSON은 "data" 키, fallback "price_series")
    raw_series: list = raw.get("data", raw.get("price_series", []))
    series = raw_series[-period_days:] if len(raw_series) > period_days else raw_series

    # 2) reference lines
    ref_lines = []
    for i, rl in enumerate(raw.get("reference_lines", [])):
        line_label = rl.get("label", "")
        ref_lines.append({
            "line_id": f"rl_{i + 1}",
            "line_type": line_label,        # e.g. "WEEK_52_HIGH"
            "value": rl["value"],
            "label": line_label,
            "style_hint": rl.get("color_hint", ""),
        })

    # 3) event markers
    markers = []
    for i, em in enumerate(raw.get("event_markers", [])):
        markers.append({
            "marker_id": f"em_{i + 1}",
            "date": em["date"],
            "event_type": em.get("event_type", ""),
            "label": em.get("label", ""),
            "detail": em.get("description", None),
            "is_catalyst_related": em.get("event_type") == "EARNINGS_RELEASE",
        })

    # 4) interest range band
    irb_raw = raw.get("interest_range_band")
    irb = None
    if irb_raw:
        irb = {
            "lower_bound": irb_raw["lower_bound"],
            "upper_bound": irb_raw["upper_bound"],
            "label": irb_raw.get("label", "관심 가격 구간"),
            "conditional_note": irb_raw.get("label", ""),
        }

    chart_as_of = series[-1]["date"] if series else raw.get("data_to", "")

    return {
        "ticker": raw.get("ticker", ""),
        "chart_as_of": chart_as_of,
        "period_days": period_days,
        "price_series": series,
        "event_markers": markers,
        "reference_lines": ref_lines,
        "interest_range_band": irb,
    }


@router.get("/chart/{ticker}")
async def get_chart_data(ticker: str, period_days: int = Query(default=365, ge=30, le=730)):
    """차트 데이터 반환 (가격 시계열 + 이벤트마커 + 참조선 + 관심구간)"""
    raw = file_store.get_chart_data(ticker)
    if not raw:
        return {
            "data": {
                "ticker": ticker.upper(),
                "chart_as_of": "2025-03-14",
                "period_days": period_days,
                **_EMPTY_CHART,
            }
        }

    return {"data": _transform_chart(raw, period_days)}
