"""FMP(Financial Modeling Prep) 기반 데이터 제공자.

필요 환경변수:
    FMP_API_KEY=your_key_here

FMP API 문서: https://financialmodelingprep.com/developer/docs
"""
import logging
from typing import Optional
import httpx

from app.services.provider.base import IDataProvider

logger = logging.getLogger(__name__)


_BASE = "https://financialmodelingprep.com/api"


class FMPDataProvider(IDataProvider):
    """FMP REST API를 사용하는 실데이터 제공자."""

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError(
                "FMP_API_KEY가 설정되지 않았습니다. "
                ".env에서 FMP_API_KEY=<your_key>를 설정해주세요."
            )
        self._key = api_key
        self._client = httpx.Client(timeout=15.0)

    def _get(self, path: str, extra: dict | None = None, **kwargs) -> dict | list | None:
        """
        FMP API GET 요청.
        - extra: Python 예약어(from 등)가 포함된 파라미터는 dict로 전달
        - kwargs: 일반 파라미터 키워드 인자
        """
        url = f"{_BASE}{path}"
        params: dict = {**kwargs}
        if extra:
            params.update(extra)
        params["apikey"] = self._key
        try:
            resp = self._client.get(url, params=params)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            logger.warning("FMP API HTTP error %s: %s", e.response.status_code, path)
            return None
        except httpx.HTTPError as e:
            logger.warning("FMP API 연결 오류: %s", e)
            return None
        except Exception as e:
            logger.warning("FMP API 예외: %s", e)
            return None

    # ── IDataProvider 구현 ────────────────────────────────────────

    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """
        FMP /v3/stock-screener 엔드포인트로 후보 종목 조회.

        실제 연동 시 필터 파라미터 매핑:
          min_market_cap_usd_b → marketCapMoreThan (단위: M)
          exchange → NYSE,NASDAQ
        """
        min_cap_m = filters.get("min_market_cap_usd_b", 2.0) * 1000
        data = self._get(
            "/v3/stock-screener",
            marketCapMoreThan=int(min_cap_m),
            exchange="NYSE,NASDAQ",
            country="US",
            limit=200,
        )
        if not isinstance(data, list):
            return []

        candidates = []
        for item in data:
            candidates.append({
                "ticker": item.get("symbol", ""),
                "company_name": item.get("companyName", ""),
                "sector": item.get("sector", ""),
                "market_cap_usd_b": (item.get("marketCap") or 0) / 1e9,
                "avg_daily_volume_m": (item.get("volume") or 0) / 1e6,
                "has_operating_income": True,   # screener 결과는 상장사 기준
                "is_adr": False,
                "in_bankruptcy": False,
                "exchange": item.get("exchangeShortName", ""),
            })
        return candidates

    def get_stock_snapshot(self, ticker: str) -> Optional[dict]:
        """
        FMP /v3/profile + /v3/ratios 조합으로 기본 스냅샷 생성.
        실제 연동에서는 추가 엔드포인트(income-statement 등)로 보완 필요.
        """
        profile_data = self._get(f"/v3/profile/{ticker}")
        if not isinstance(profile_data, list) or not profile_data:
            return None
        profile = profile_data[0]

        ratios_data = self._get(f"/v3/ratios-ttm/{ticker}")
        ratios = ratios_data[0] if isinstance(ratios_data, list) and ratios_data else {}

        # 필드명을 valuation/analysis 엔진이 기대하는 키로 정규화
        snapshot = {
            "ticker": ticker,
            "company_name": profile.get("companyName", ""),
            "sector": profile.get("sector", ""),
            "industry": profile.get("industry", ""),
            "market_cap_usd_b": (profile.get("mktCap") or 0) / 1e9,
            "current_price": profile.get("price"),
            "short_description": profile.get("description", ""),
            "headquarters": profile.get("city", ""),
            "exchange": profile.get("exchangeShortName", ""),
            # analysis 엔진이 사용하는 키 이름
            "fwd_per": ratios.get("priceEarningsRatioTTM"),        # Fwd PER
            "pb": ratios.get("priceToBookRatioTTM"),               # P/B
            "ev_ebitda": ratios.get("enterpriseValueMultipleTTM"), # EV/EBITDA
            "trailing_per": ratios.get("peRatioTTM"),
            "ps": ratios.get("priceToSalesRatioTTM"),
            "p_fcf": ratios.get("priceToFreeCashFlowsRatioTTM"),
            # 52주 가격 맥락 (screener 결과에서 없을 수 있음)
            "52w_high": profile.get("range", "").split("-")[-1].strip() if profile.get("range") else None,
            "52w_low": profile.get("range", "").split("-")[0].strip() if profile.get("range") else None,
        }

        # 재무 데이터 포함 (report_builder._assemble() 이 financials 필드로 직접 사용)
        financials = self.get_financials(ticker)
        if financials:
            snapshot["financials"] = financials

        return snapshot

    def get_price_series(self, ticker: str, period_days: int) -> list[dict]:
        """FMP /v3/historical-price-full/{ticker} 주간 OHLCV 반환."""
        data = self._get(
            f"/v3/historical-price-full/{ticker}",
            serietype="line",
            timeseries=period_days,
        )
        if not isinstance(data, dict):
            return []
        historical = data.get("historical", [])
        return [
            {
                "date": item["date"],
                "open": item.get("open"),
                "high": item.get("high"),
                "low": item.get("low"),
                "close": item.get("close"),
                "volume": item.get("volume"),
            }
            for item in reversed(historical)  # 오래된 순으로 정렬
        ]

    def get_financials(self, ticker: str) -> Optional[dict]:
        """
        FMP /v3/income-statement + /v3/key-metrics-ttm 로 재무 요약 반환.

        report_builder._assemble() 의 financials 필드 구조에 맞춤:
          revenue_ttm_b, revenue_growth_yoy_pct, operating_income_ttm_b,
          operating_margin_pct, net_income_ttm_b, eps_ttm, eps_fwd_consensus,
          eps_revision_trend, fcf_ttm_b, net_debt_b, net_debt_to_ebitda,
          interest_coverage_ratio, roe_pct
        """
        def _dv(v, status="CONFIRMED"):
            return {"value": v, "status": status if v is not None else "UNAVAILABLE"}

        # 소득계산서 최근 2기 (YoY 성장률 계산용)
        income_data = self._get(f"/v3/income-statement/{ticker}", limit=2)
        rows = income_data if isinstance(income_data, list) else []
        curr = rows[0] if rows else {}
        prev = rows[1] if len(rows) > 1 else {}

        # TTM 지표 (ROE, FCF yield, D/E 등)
        metrics_data = self._get(f"/v3/key-metrics-ttm/{ticker}")
        m = metrics_data[0] if isinstance(metrics_data, list) and metrics_data else {}

        # ── 수익 ────────────────────────────────────────────────
        rev_curr = curr.get("revenue")
        rev_prev = prev.get("revenue")
        rev_b    = round(rev_curr / 1e9, 2) if rev_curr else None

        rev_growth = None
        if rev_curr and rev_prev and rev_prev != 0:
            rev_growth = round((rev_curr - rev_prev) / abs(rev_prev) * 100, 1)

        op_inc = curr.get("operatingIncome")
        op_inc_b = round(op_inc / 1e9, 4) if op_inc else None
        op_margin = (
            round(curr.get("operatingIncomeRatio", 0) * 100, 1)
            if curr.get("operatingIncomeRatio") is not None else None
        )

        net_inc = curr.get("netIncome")
        net_inc_b = round(net_inc / 1e9, 4) if net_inc else None

        eps = curr.get("eps")

        # ── EPS 컨센서스 (key-metrics-ttm에 없으므로 UNAVAILABLE) ──
        eps_fwd = None

        # ── FCF (key-metrics-ttm의 freeCashFlowPerShareTTM * 주식 수로 근사) ──
        fcf_ps   = m.get("freeCashFlowPerShareTTM")
        shares   = m.get("weightedAverageSharesOutTTM") or curr.get("weightedAverageShsOut")
        fcf_b    = round(fcf_ps * shares / 1e9, 4) if (fcf_ps and shares) else None

        # ── 부채 지표 ────────────────────────────────────────────
        net_debt_b = None
        cash = curr.get("cashAndCashEquivalents") or curr.get("netCashProvidedByOperatingActivities")
        total_debt = curr.get("totalDebt") or curr.get("longTermDebt")
        if cash is not None and total_debt is not None:
            net_debt_b = round((total_debt - cash) / 1e9, 4)

        nd_ebitda = m.get("netDebtToEBITDATTM")
        int_cov   = m.get("interestCoverageTTM")
        roe       = round(m.get("roeTTM") * 100, 1) if m.get("roeTTM") is not None else None

        if not curr and not m:
            return None

        return {
            "status": "CONFIRMED",
            "fiscal_year": str(curr.get("calendarYear", ""))[:4] or "N/A",
            "revenue_ttm_b":           _dv(rev_b),
            "revenue_growth_yoy_pct":  _dv(rev_growth),
            "operating_income_ttm_b":  _dv(op_inc_b),
            "operating_margin_pct":    _dv(op_margin),
            "net_income_ttm_b":        _dv(net_inc_b),
            "eps_ttm":                 _dv(eps),
            "eps_fwd_consensus":       _dv(eps_fwd, "UNAVAILABLE"),
            "eps_revision_trend":      "NEUTRAL",
            "fcf_ttm_b":               _dv(fcf_b),
            "net_debt_b":              _dv(net_debt_b),
            "net_debt_to_ebitda":      _dv(nd_ebitda),
            "interest_coverage_ratio": _dv(int_cov),
            "roe_pct":                 _dv(roe),
        }

    def get_consensus_data(self, ticker: str) -> Optional[dict]:
        """FMP /v4/price-target-consensus 기반 컨센서스 데이터."""
        data = self._get(f"/v4/price-target-consensus", symbol=ticker)
        if not isinstance(data, list) or not data:
            return None
        item = data[0]
        return {
            "target_mean_price": item.get("targetMean"),
            "target_high_price": item.get("targetHigh"),
            "target_low_price": item.get("targetLow"),
            "analyst_count": item.get("numberOfAnalysts"),
        }

    def get_earnings_calendar(self, ticker: str, days_ahead: int) -> list[dict]:
        """FMP /v3/earning_calendar 기반 어닝 일정.
        `from`이 Python 예약어이므로 extra dict로 전달.
        """
        from datetime import date, timedelta
        today = date.today().isoformat()
        end = (date.today() + timedelta(days=days_ahead)).isoformat()
        data = self._get(
            "/v3/earning_calendar",
            extra={"from": today, "to": end},
            symbol=ticker,
        )
        if not isinstance(data, list):
            return []
        return [
            {"date": item["date"], "type": "EARNINGS_RELEASE"}
            for item in data
            if item.get("symbol") == ticker
        ]
