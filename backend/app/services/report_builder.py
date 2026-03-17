"""
ReportBuilder — screening 결과 + analysis 엔진 → StockReport 조립

흐름:
  1. provider.get_stock_snapshot(ticker) → 완전한 mock JSON 또는 최소 스냅샷
  2. 각 analysis 엔진 호출
  3. StockReport JSON 조립 + 반환

provider 교체 시 build_report() 인터페이스는 변경 없음.
"""
import uuid
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings
from app.services.provider.base import IDataProvider
from app.services.analysis.valuation import compute_valuation
from app.services.analysis.catalyst import assess_catalysts
from app.services.analysis.risk import assess_risks
from app.services.analysis.interest_range import compute_interest_range


class ReportBuilder:
    def __init__(self, provider: IDataProvider):
        self.provider = provider

    def build_report(
        self,
        ticker: str,
        report_id: str,
        *,
        generate_narrative: bool = False,
    ) -> Optional[dict]:
        """
        단일 종목 StockReport 딕셔너리 반환.
        None → 데이터 없음 (404 처리)
        """
        snapshot = self.provider.get_stock_snapshot(ticker)
        if not snapshot:
            return None

        # ── 외부 데이터 수집 ────────────────────────────────────
        consensus = self.provider.get_consensus_data(ticker)
        earnings = self.provider.get_earnings_calendar(ticker, days_ahead=90)

        # ── Analysis 엔진 ───────────────────────────────────────
        valuation = compute_valuation(snapshot)
        catalyst_assessment = assess_catalysts(snapshot, consensus, earnings)
        structural_risks, short_term_risks = assess_risks(snapshot)
        interest_range = compute_interest_range(snapshot, valuation)

        # ── 이미 완전한 StockReport JSON인 경우 (mock) ──────────
        if _is_full_report(snapshot):
            report = dict(snapshot)
            report["valuation"] = valuation
            report["catalyst_assessment"] = catalyst_assessment
            report["structural_risks"] = structural_risks
            report["short_term_risks"] = short_term_risks
            report["interest_price_range"] = interest_range
            if generate_narrative:
                report["analyst_style_summary"] = _generate_narrative(report)
            return report

        # ── 최소 스냅샷에서 조립 (real provider scaffold) ───────
        # price_context 계산을 위해 가격 시계열 수집 (없으면 empty 반환)
        price_series = []
        if snapshot.get("price_context") is None:
            price_series = self.provider.get_price_series(ticker, period_days=365)

        report = _assemble(ticker, report_id, snapshot, valuation,
                           catalyst_assessment, structural_risks, short_term_risks,
                           interest_range, price_series)
        if generate_narrative:
            report["analyst_style_summary"] = _generate_narrative(report)
        return report


def _is_full_report(snapshot: dict) -> bool:
    """snapshot이 이미 완전한 StockReport인지 판별."""
    required = ("report_item_id", "valuation", "financials",
                 "undervaluation_judgment", "analyst_style_summary")
    return all(k in snapshot for k in required)


def _assemble(
    ticker: str,
    report_id: str,
    snap: dict,
    valuation: dict,
    catalyst: dict,
    struct_risks: list,
    short_risks: list,
    interest_range: dict,
    price_series: list | None = None,
) -> dict:
    """최소 스냅샷 → StockReport 조립 (real provider용)."""
    now = datetime.now(timezone.utc).isoformat()
    item_id = f"ri_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{report_id.split('_')[-1]}_{ticker}"

    discount_pct = valuation.get("valuation_discount_vs_sector", {}).get("discount_pct")
    is_discounted = discount_pct is not None and discount_pct >= 10.0
    met_count = catalyst.get("met_count", 0)

    if is_discounted and met_count >= 2:
        signal = "STRONG_SIGNAL"
    elif is_discounted and met_count >= 1:
        signal = "MODERATE_SIGNAL"
    elif is_discounted:
        signal = "WEAK_SIGNAL"
    else:
        signal = "NO_SIGNAL"

    return {
        "report_item_id": item_id,
        "report_id": report_id,
        "ticker": ticker,
        "company_name": snap.get("company_name", ticker),
        "exchange": snap.get("exchange", "NYSE"),
        "sector": snap.get("sector", "Unknown"),
        "industry": snap.get("industry", ""),
        "stock_info": {
            "short_description": snap.get("short_description", "데이터 준비 중."),
            "headquarters": snap.get("headquarters"),
            "market_cap_usd_b": snap.get("market_cap_usd_b", 0),
            "employee_count": {"value": snap.get("employee_count"), "status": "UNVERIFIED"},
            "fiscal_year_end": snap.get("fiscal_year_end", "12-31"),
        },
        "current_price": {
            "value": snap.get("current_price", snap.get("price", 0)),
            "currency": "USD",
            "as_of": now,
        },
        "price_context": snap.get("price_context") or _compute_price_context(snap, price_series or []),
        "interest_price_range": interest_range,
        "valuation": valuation,
        "financials": snap.get("financials", _empty_financials()),
        "undervaluation_judgment": {
            "is_discounted_vs_sector": is_discounted,
            "is_discounted_vs_history": False,
            "combined_signal": signal,
            "primary_discount_drivers": [valuation.get("primary_metric", "Fwd PER")],
            "discount_narrative": {
                "content": f"현재 {valuation.get('primary_metric', 'Fwd PER')} 기준 섹터 대비 저평가 구간에 위치.",
                "status": "AI_GENERATED",
                "data_fields_referenced": [],
            },
        },
        "catalyst_assessment": catalyst,
        "bull_case_points": snap.get("bull_case_points", []),
        "bear_case_points": snap.get("bear_case_points", []),
        "structural_risks": struct_risks,
        "short_term_risks": short_risks,
        "analyst_style_summary": snap.get("analyst_style_summary", _placeholder_summary()),
        "data_quality_flags": [],
        "data_sources": [
            {
                "source_id": f"src_{settings.DATA_PROVIDER_MODE}_001",
                "provider_name": settings.DATA_PROVIDER_MODE.upper(),
                "data_category": "FINANCIALS",
                "as_of": now,
            }
        ],
        "disclaimer_blocks": _default_disclaimers(),
        "publication_meta": {
            "status": "DRAFT",
            "created_at": now,
            "reviewed_by": None,
            "reviewed_at": None,
            "published_at": None,
            "last_updated_at": now,
        },
    }


def _compute_price_context(snap: dict, series: list[dict]) -> dict:
    """가격 시계열 + 스냅샷 52w 값으로 price_context 계산 (real provider용)."""
    def _dv(v):
        return {"value": round(float(v), 2) if v is not None else None,
                "status": "CONFIRMED" if v is not None else "UNAVAILABLE"}

    current = snap.get("current_price") or snap.get("price")
    high_52w = snap.get("52w_high")
    low_52w = snap.get("52w_low")

    # 시계열에서 52w 범위 보완
    if series:
        closes = [item.get("close") for item in series if item.get("close") is not None]
        if closes:
            if high_52w is None:
                high_52w = max(closes)
            if low_52w is None:
                low_52w = min(closes)

    # 52w 위치, 고점 대비 하락
    pos_pct = None
    drawdown = None
    if high_52w and low_52w and current:
        try:
            high_f = float(high_52w)
            low_f = float(low_52w)
            curr_f = float(current)
            if high_f != low_f:
                pos_pct = round((curr_f - low_f) / (high_f - low_f) * 100, 1)
            drawdown = round((high_f - curr_f) / high_f * 100, 1)
        except (TypeError, ValueError):
            pass

    def _pct_change(bars_back: int):
        if len(series) <= bars_back:
            return None
        past = series[-(bars_back + 1)].get("close")
        now_close = series[-1].get("close")
        if past and now_close:
            return round((now_close - past) / past * 100, 1)
        return None

    return {
        "week_52_high": _dv(float(high_52w) if high_52w else None),
        "week_52_low": _dv(float(low_52w) if low_52w else None),
        "week_52_position_pct": _dv(pos_pct),
        "drawdown_from_52w_high_pct": _dv(drawdown),
        "price_1m_change_pct": _dv(_pct_change(4)),
        "price_3m_change_pct": _dv(_pct_change(13)),
        "price_6m_change_pct": _dv(_pct_change(26)),
        "price_ytd_change_pct": {"value": None, "status": "UNAVAILABLE"},
        "as_of": datetime.now(timezone.utc).date().isoformat(),
    }


def _empty_price_context() -> dict:
    na = {"value": None, "status": "UNAVAILABLE"}
    return {
        "week_52_high": na, "week_52_low": na,
        "week_52_position_pct": na, "drawdown_from_52w_high_pct": na,
        "price_1m_change_pct": na, "price_3m_change_pct": na,
        "price_6m_change_pct": na, "price_ytd_change_pct": na,
        "as_of": datetime.now(timezone.utc).date().isoformat(),
    }


def _empty_financials() -> dict:
    na = {"value": None, "status": "UNAVAILABLE"}
    return {
        "status": "UNAVAILABLE",
        "fiscal_year": "N/A",
        "revenue_ttm_b": na, "revenue_growth_yoy_pct": na,
        "operating_income_ttm_b": na, "operating_margin_pct": na,
        "net_income_ttm_b": na, "eps_ttm": na,
        "eps_fwd_consensus": na, "eps_revision_trend": "NEUTRAL",
        "fcf_ttm_b": na, "net_debt_b": na, "net_debt_to_ebitda": na,
        "interest_coverage_ratio": na, "roe_pct": na,
    }


def _placeholder_summary() -> dict:
    now = datetime.now(timezone.utc).isoformat()
    ph = {
        "content": "분석 서술 준비 중입니다.",
        "status": "PLACEHOLDER",
        "data_fields_referenced": [],
    }
    return {
        "why_discounted": ph,
        "why_worth_revisiting": ph,
        "key_risks_narrative": ph,
        "investment_context": ph,
        "generated_at": now,
        "model_id": "placeholder",
        "reviewer_approved": False,
    }


def _generate_narrative(report: dict) -> dict:
    """generate_narrative=True 시 호출. 실패해도 placeholder 반환."""
    try:
        from app.services.narrative.generator import generate_narrative
        return generate_narrative(report)
    except Exception:
        return _placeholder_summary()


def _default_disclaimers() -> list:
    return [
        {
            "block_id": "dis_h_001",
            "position": "HEADER",
            "content": (
                "본 리포트는 투자 권유가 아닙니다. "
                "제공된 정보는 참고용이며 투자 결정의 근거로 사용할 수 없습니다."
            ),
            "is_required": True,
        },
        {
            "block_id": "dis_f_001",
            "position": "FOOTER",
            "content": (
                "본 리포트의 모든 내용은 정보 제공 목적으로만 작성되었습니다. "
                "투자에는 원금 손실 위험이 있으며, 과거 성과는 미래를 보장하지 않습니다."
            ),
            "is_required": True,
        },
    ]
