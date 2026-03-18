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


# ── yfinance 모드용 정적 유니버스 ──────────────────────────────
# yfinance는 스크리너 API가 없으므로 대표 미국 주식 목록을 내장.
# 섹터별 분산 / 시총 $2B 이상 기준으로 선별한 40개 종목.
# 각 항목의 시총·거래량은 대략적 추정값 -- 실제값은 get_stock_snapshot 으로 보완됨.
_YFINANCE_STATIC_UNIVERSE: list[dict] = [
    # Industrials
    {"ticker": "HON",  "company_name": "Honeywell International", "sector": "Industrials",
     "market_cap_usd_b": 130.0, "avg_daily_volume_m": 2.5, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "EMR",  "company_name": "Emerson Electric", "sector": "Industrials",
     "market_cap_usd_b": 55.0, "avg_daily_volume_m": 2.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "ITW",  "company_name": "Illinois Tool Works", "sector": "Industrials",
     "market_cap_usd_b": 65.0, "avg_daily_volume_m": 1.2, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "GWW",  "company_name": "W.W. Grainger", "sector": "Industrials",
     "market_cap_usd_b": 43.0, "avg_daily_volume_m": 0.3, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Financials
    {"ticker": "USB",  "company_name": "U.S. Bancorp", "sector": "Financials",
     "market_cap_usd_b": 65.0, "avg_daily_volume_m": 6.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "TFC",  "company_name": "Truist Financial", "sector": "Financials",
     "market_cap_usd_b": 50.0, "avg_daily_volume_m": 8.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "CFG",  "company_name": "Citizens Financial Group", "sector": "Financials",
     "market_cap_usd_b": 16.0, "avg_daily_volume_m": 4.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "HBAN", "company_name": "Huntington Bancshares", "sector": "Financials",
     "market_cap_usd_b": 18.0, "avg_daily_volume_m": 9.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Health Care
    {"ticker": "CVS",  "company_name": "CVS Health", "sector": "Health Care",
     "market_cap_usd_b": 75.0, "avg_daily_volume_m": 7.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "HCA",  "company_name": "HCA Healthcare", "sector": "Health Care",
     "market_cap_usd_b": 70.0, "avg_daily_volume_m": 1.2, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "MCK",  "company_name": "McKesson Corporation", "sector": "Health Care",
     "market_cap_usd_b": 60.0, "avg_daily_volume_m": 0.7, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "CI",   "company_name": "Cigna Group", "sector": "Health Care",
     "market_cap_usd_b": 80.0, "avg_daily_volume_m": 1.5, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Consumer Staples
    {"ticker": "KO",   "company_name": "Coca-Cola", "sector": "Consumer Staples",
     "market_cap_usd_b": 260.0, "avg_daily_volume_m": 13.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "PEP",  "company_name": "PepsiCo", "sector": "Consumer Staples",
     "market_cap_usd_b": 220.0, "avg_daily_volume_m": 4.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "MO",   "company_name": "Altria Group", "sector": "Consumer Staples",
     "market_cap_usd_b": 90.0, "avg_daily_volume_m": 8.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "KHC",  "company_name": "Kraft Heinz", "sector": "Consumer Staples",
     "market_cap_usd_b": 30.0, "avg_daily_volume_m": 7.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Energy
    {"ticker": "VLO",  "company_name": "Valero Energy", "sector": "Energy",
     "market_cap_usd_b": 44.0, "avg_daily_volume_m": 3.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "PSX",  "company_name": "Phillips 66", "sector": "Energy",
     "market_cap_usd_b": 50.0, "avg_daily_volume_m": 3.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "MPC",  "company_name": "Marathon Petroleum", "sector": "Energy",
     "market_cap_usd_b": 56.0, "avg_daily_volume_m": 3.5, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "OKE",  "company_name": "ONEOK Inc.", "sector": "Energy",
     "market_cap_usd_b": 45.0, "avg_daily_volume_m": 3.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Information Technology
    {"ticker": "CSCO", "company_name": "Cisco Systems", "sector": "Information Technology",
     "market_cap_usd_b": 200.0, "avg_daily_volume_m": 15.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "HPQ",  "company_name": "HP Inc.", "sector": "Information Technology",
     "market_cap_usd_b": 32.0, "avg_daily_volume_m": 7.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "INTC", "company_name": "Intel Corporation", "sector": "Information Technology",
     "market_cap_usd_b": 100.0, "avg_daily_volume_m": 40.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "IBM",  "company_name": "IBM", "sector": "Information Technology",
     "market_cap_usd_b": 160.0, "avg_daily_volume_m": 3.5, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Communication Services
    {"ticker": "VZ",   "company_name": "Verizon Communications", "sector": "Communication Services",
     "market_cap_usd_b": 175.0, "avg_daily_volume_m": 18.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "T",    "company_name": "AT&T Inc.", "sector": "Communication Services",
     "market_cap_usd_b": 140.0, "avg_daily_volume_m": 35.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "PARA", "company_name": "Paramount Global", "sector": "Communication Services",
     "market_cap_usd_b": 8.0, "avg_daily_volume_m": 9.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Consumer Discretionary
    {"ticker": "F",    "company_name": "Ford Motor Company", "sector": "Consumer Discretionary",
     "market_cap_usd_b": 45.0, "avg_daily_volume_m": 50.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "GM",   "company_name": "General Motors", "sector": "Consumer Discretionary",
     "market_cap_usd_b": 47.0, "avg_daily_volume_m": 20.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "LKQ",  "company_name": "LKQ Corporation", "sector": "Consumer Discretionary",
     "market_cap_usd_b": 9.0, "avg_daily_volume_m": 1.5, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Materials
    {"ticker": "LYB",  "company_name": "LyondellBasell Industries", "sector": "Materials",
     "market_cap_usd_b": 25.0, "avg_daily_volume_m": 2.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "MOS",  "company_name": "The Mosaic Company", "sector": "Materials",
     "market_cap_usd_b": 8.0, "avg_daily_volume_m": 4.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Utilities
    {"ticker": "SO",   "company_name": "Southern Company", "sector": "Utilities",
     "market_cap_usd_b": 75.0, "avg_daily_volume_m": 4.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "PCG",  "company_name": "PG&E Corporation", "sector": "Utilities",
     "market_cap_usd_b": 35.0, "avg_daily_volume_m": 8.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    # Real Estate
    {"ticker": "VNO",  "company_name": "Vornado Realty Trust", "sector": "Real Estate",
     "market_cap_usd_b": 6.0, "avg_daily_volume_m": 2.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
    {"ticker": "SLG",  "company_name": "SL Green Realty", "sector": "Real Estate",
     "market_cap_usd_b": 3.0, "avg_daily_volume_m": 1.0, "has_operating_income": True, "is_adr": False, "in_bankruptcy": False},
]


class YFinanceDataProvider(IDataProvider):
    """yfinance 라이브러리 기반 실데이터 제공자 (가격 중심)."""

    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """
        yfinance는 스크리너 API가 없으므로 내장 정적 유니버스 반환.
        각 후보의 시총/거래량은 추정값이며, pipeline._enrich_candidate_for_scoring()
        에서 get_stock_snapshot() 호출로 실제값으로 보완된다.
        """
        min_cap = filters.get("min_market_cap_usd_b", 2.0)
        candidates = [
            c for c in _YFINANCE_STATIC_UNIVERSE
            if c["market_cap_usd_b"] >= min_cap
        ]
        logger.info("YFinance 정적 유니버스: %d개 후보 (시총 $%.1fB 이상)", len(candidates), min_cap)
        return candidates

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
