"""데이터 제공자 추상 인터페이스 - 실제 구현은 mock/fmp/yfinance provider에서"""
from abc import ABC, abstractmethod
from typing import Optional


class IDataProvider(ABC):
    """모든 데이터 제공자가 구현해야 하는 인터페이스"""

    @abstractmethod
    def get_universe_candidates(self, filters: dict) -> list[dict]:
        """유니버스 필터링 후 후보 종목 목록 반환"""
        pass

    @abstractmethod
    def get_stock_snapshot(self, ticker: str) -> Optional[dict]:
        """종목의 전체 데이터 스냅샷 반환"""
        pass

    @abstractmethod
    def get_price_series(self, ticker: str, period_days: int) -> list[dict]:
        """가격 시계열 데이터 반환"""
        pass

    @abstractmethod
    def get_consensus_data(self, ticker: str) -> Optional[dict]:
        """애널리스트 컨센서스 데이터 반환 (Catalyst B용)"""
        pass

    @abstractmethod
    def get_earnings_calendar(self, ticker: str, days_ahead: int) -> list[dict]:
        """어닝 일정 반환 (Catalyst A용)"""
        pass
