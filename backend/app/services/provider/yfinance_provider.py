"""yfinance 기반 데이터 제공자 (가격 데이터 특화, 무료).

주의:
  - yfinance는 Yahoo Finance 비공식 API를 사용합니다.
  - 컨센서스/어닝 데이터의 신뢰도가 낮아 Catalyst A/B는 UNVERIFIABLE 처리될 수 있습니다.
  - 프로덕션에서는 hybrid_provider (yfinance 가격 + FMP 컨센서스) 권장.

필요 패키지:
    pip install yfinance>=0.2.40
"""
import logging
import math
from datetime import date, timedelta
from typing import Optional

from app.services.provider.base import IDataProvider

logger = logging.getLogger(__name__)


def _yf():
    """yfinance 지연 임포트 — 패키지 없을 때 ImportError 즉시 노출."""
    try:
        import yfinance as yf
        return yf
    except ImportError:
        raise ImportError(
            "yfinance 패키지가 설치되지 않았습니다: pip install yfinance>=0.2.40"
        )


class YFinanceDataProvider(IDataProvider):
    """yfinance 라이브러리 기반 실데이터 제공자 (가격 중심)."""

    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """
        yfinance는 유니버스 스크리닝을 지원하지 않습니다.
        실제 사용 시 별도 유니버스 리스트(CSV 등)와 조합해야 합니다.
        """
        logger.warning("YFinanceDataProvider.get_universe_candidates() — 지원 안 됨, 빈 리스트 반환")
        return []

    def get_stock_snapshot(self, ticker: str) -> Optional[dict]:
        """yfinance Ticker.info로 기본 스냅샷 반환."""
        yf = _yf()
        try:
            info = yf.Ticker(ticker).info
        except Exception as e:
            logger.warning("yfinance info 조회 실패 %s: %s", ticker, e)
            return None

        if not info or (info.get("currentPrice") is None and info.get("regularMarketPrice") is None):
            return None

        price = info.get("currentPrice") or info.get("regularMarketPrice")

        return {
            "ticker": ticker,
            "company_name": info.get("longName", ""),
            "sector": info.get("sector", ""),
            "industry": info.get("industry", ""),
            "market_cap_usd_b": (info.get("marketCap") or 0) / 1e9,
            "current_price": price,
            "short_description": info.get("longBusinessSummary", "")[:500] if info.get("longBusinessSummary") else "",
            "headquarters": f"{info.get('city', '')}, {info.get('country', '')}".strip(", "),
            "exchange": info.get("exchange", ""),
            "employee_count": info.get("fullTimeEmployees"),
            # analysis 엔진이 사용하는 키 이름
            "fwd_per": info.get("forwardPE"),
            "pb": info.get("priceToBook"),
            "ev_ebitda": info.get("enterpriseToEbitda"),
            "trailing_per": info.get("trailingPE"),
            "ps": info.get("priceToSalesTrailing12Months"),
            # 52주 가격 맥락
            "52w_high": info.get("fiftyTwoWeekHigh"),
            "52w_low": info.get("fiftyTwoWeekLow"),
        }

    def get_price_series(self, ticker: str, period_days: int) -> list[dict]:
        """yfinance로 주간 OHLCV 반환 (날짜 범위 기반)."""
        yf = _yf()
        try:
            end_dt = date.today()
            start_dt = end_dt - timedelta(days=period_days + 30)  # 여유분 포함
            hist = yf.Ticker(ticker).history(
                start=start_dt.isoformat(),
                end=end_dt.isoformat(),
                interval="1wk",
            )
        except Exception as e:
            logger.warning("yfinance history 조회 실패 %s: %s", ticker, e)
            return []

        if hist is None or hist.empty:
            return []

        series = []
        for dt, row in hist.iterrows():
            series.append({
                "date": dt.strftime("%Y-%m-%d"),
                "open": round(float(row["Open"]), 2),
                "high": round(float(row["High"]), 2),
                "low": round(float(row["Low"]), 2),
                "close": round(float(row["Close"]), 2),
                "volume": int(row["Volume"]),
            })

        return series[-period_days:] if len(series) > period_days else series

    def get_consensus_data(self, ticker: str) -> Optional[dict]:
        """
        yfinance analyst_price_target (단수형) 또는 analyst_price_targets (복수형) 시도.
        버전에 따라 속성명이 다름.
        """
        yf = _yf()
        try:
            t = yf.Ticker(ticker)

            # yfinance 0.2.x: analyst_price_targets (dict)
            targets = getattr(t, "analyst_price_targets", None)
            if targets and isinstance(targets, dict) and "mean" in targets:
                return {
                    "target_mean_price": targets.get("mean"),
                    "target_high_price": targets.get("high"),
                    "target_low_price": targets.get("low"),
                    "analyst_count": targets.get("numberOfAnalysts"),
                }

            # Fallback: info의 목표가 필드
            info = t.info
            target = info.get("targetMeanPrice")
            if target:
                return {
                    "target_mean_price": target,
                    "target_high_price": info.get("targetHighPrice"),
                    "target_low_price": info.get("targetLowPrice"),
                    "analyst_count": info.get("numberOfAnalystOpinions"),
                }
        except Exception as e:
            logger.warning("yfinance consensus 조회 실패 %s: %s", ticker, e)

        return None

    def get_earnings_calendar(self, ticker: str, days_ahead: int) -> list[dict]:
        """yfinance calendar에서 어닝 날짜 반환."""
        yf = _yf()
        try:
            cal = yf.Ticker(ticker).calendar
            if cal is None:
                return []

            # yfinance 버전에 따라 dict 또는 DataFrame 반환
            if hasattr(cal, "to_dict"):
                cal = cal.to_dict()

            earnings_date = cal.get("Earnings Date") or cal.get("earnings_date")
            if not earnings_date:
                return []

            if hasattr(earnings_date, "__iter__") and not isinstance(earnings_date, str):
                dates = list(earnings_date)
            else:
                dates = [earnings_date]

            cutoff = date.today() + timedelta(days=days_ahead)
            return [
                {"date": str(d)[:10], "type": "EARNINGS_RELEASE"}
                for d in dates
                if str(d)[:10] <= cutoff.isoformat()
            ]
        except Exception as e:
            logger.warning("yfinance calendar 조회 실패 %s: %s", ticker, e)
            return []
