"""Mock 데이터 제공자 - JSON 파일 기반"""
from typing import Optional
from app.services.provider.base import IDataProvider
from app.storage.file_store import file_store


# mock consensus 목표가 테이블
_MOCK_CONSENSUS: dict[str, dict] = {
    "MFGI": {"target_mean_price": 55.0, "analyst_count": 8},
    "RVNC": {"target_mean_price": 34.0, "analyst_count": 6},
    # HLTH: 미포함 → Catalyst B UNVERIFIABLE 시뮬레이션
    "CSTM": {"target_mean_price": 38.5, "analyst_count": 5},
    "ENXT": {"target_mean_price": 26.0, "analyst_count": 7},
    "NXST": {"target_mean_price": 160.0, "analyst_count": 4},
    "ATHN": {"target_mean_price": 25.0, "analyst_count": 3},
}

# mock 어닝 일정 (향후 90일 이내 실적 예정)
_MOCK_EARNINGS: dict[str, list[dict]] = {
    "MFGI": [{"date": "2025-04-24", "type": "EARNINGS_RELEASE"}],
    "RVNC": [{"date": "2025-04-17", "type": "EARNINGS_RELEASE"}],
    "HLTH": [{"date": "2025-05-01", "type": "EARNINGS_RELEASE"}],
    "CSTM": [{"date": "2025-05-08", "type": "EARNINGS_RELEASE"}],
    "ENXT": [{"date": "2025-05-05", "type": "EARNINGS_RELEASE"}],
}


class MockDataProvider(IDataProvider):
    """개발/테스트용 Mock 데이터 제공자."""

    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """mock universe 전체 후보 반환 (필터 전)."""
        from app.services.screening.universe_filter import MOCK_UNIVERSE
        return MOCK_UNIVERSE

    def get_stock_snapshot(self, ticker: str) -> Optional[dict]:
        """
        완전한 StockReport JSON 반환 (mock).
        개별 파일 없으면 edition StockCard fallback.
        """
        # 1) 개별 리포트 JSON (가장 상세)
        report = file_store.get_stock_report(ticker.upper(), "re_20250317_002")
        if report:
            return report

        # 2) fallback: edition StockCard
        edition = file_store.get_latest_edition()
        if not edition:
            return None
        for s in edition.get("stocks", []):
            if s["ticker"] == ticker.upper():
                return s
        return None

    def get_price_series(self, ticker: str, period_days: int) -> list[dict]:
        chart_data = file_store.get_chart_data(ticker)
        if not chart_data:
            return []
        # Mock JSON은 "data" 키 사용 (fallback: "price_series")
        series = chart_data.get("data", chart_data.get("price_series", []))
        return series[-period_days:] if len(series) > period_days else series

    def get_consensus_data(self, ticker: str) -> Optional[dict]:
        """HLTH는 None 반환 → Catalyst B UNVERIFIABLE 시뮬레이션."""
        return _MOCK_CONSENSUS.get(ticker.upper())

    def get_earnings_calendar(self, ticker: str, days_ahead: int) -> list[dict]:
        return _MOCK_EARNINGS.get(ticker.upper(), [])


mock_provider = MockDataProvider()
