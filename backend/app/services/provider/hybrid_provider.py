"""Hybrid 데이터 제공자: yfinance(가격) + FMP(컨센서스/어닝).

권장 프로덕션 구성:
  - 가격 시계열: yfinance (무료, 안정적)
  - 컨센서스/목표가: FMP (유료, 정확)
  - 어닝 캘린더: FMP (유료, 정확)
  - 유니버스/스냅샷: FMP

필요 환경변수:
    FMP_API_KEY=your_key_here
"""
from typing import Optional

from app.services.provider.base import IDataProvider
from app.services.provider.fmp_provider import FMPDataProvider
from app.services.provider.yfinance_provider import YFinanceDataProvider


class HybridDataProvider(IDataProvider):
    """yfinance(가격) + FMP(컨센서스/어닝) 결합 제공자."""

    def __init__(self, fmp_api_key: str):
        self._fmp = FMPDataProvider(api_key=fmp_api_key)
        self._yf = YFinanceDataProvider()

    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """FMP screener 사용 (유니버스는 FMP가 더 정확)."""
        return self._fmp.get_universe_candidates(filters)

    def get_stock_snapshot(self, ticker: str) -> Optional[dict]:
        """FMP profile + yfinance 가격 보완."""
        snapshot = self._fmp.get_stock_snapshot(ticker)
        if snapshot is None:
            snapshot = self._yf.get_stock_snapshot(ticker)
        elif snapshot.get("current_price") is None:
            # FMP 스냅샷에 가격이 없으면 yfinance로 보완
            yf_snap = self._yf.get_stock_snapshot(ticker)
            if yf_snap:
                snapshot["current_price"] = yf_snap.get("current_price")
                snapshot["52w_high"] = yf_snap.get("52w_high")
                snapshot["52w_low"] = yf_snap.get("52w_low")
        return snapshot

    def get_price_series(self, ticker: str, period_days: int) -> list[dict]:
        """yfinance 사용 (가격 데이터 무료 + 충분한 히스토리)."""
        series = self._yf.get_price_series(ticker, period_days)
        if not series:
            # yfinance 실패 시 FMP fallback
            series = self._fmp.get_price_series(ticker, period_days)
        return series

    def get_consensus_data(self, ticker: str) -> Optional[dict]:
        """FMP 사용 (애널리스트 컨센서스는 FMP가 더 정확)."""
        data = self._fmp.get_consensus_data(ticker)
        if data is None:
            # FMP 없으면 yfinance fallback (신뢰도 낮음)
            data = self._yf.get_consensus_data(ticker)
        return data

    def get_earnings_calendar(self, ticker: str, days_ahead: int) -> list[dict]:
        """FMP 사용 (어닝 일정은 FMP가 더 정확)."""
        events = self._fmp.get_earnings_calendar(ticker, days_ahead)
        if not events:
            events = self._yf.get_earnings_calendar(ticker, days_ahead)
        return events
