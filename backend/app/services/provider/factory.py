"""Provider factory — DATA_PROVIDER_MODE 설정에 따라 적절한 provider 반환"""
from app.core.config import settings
from app.services.provider.base import IDataProvider


def get_provider() -> IDataProvider:
    """
    .env의 DATA_PROVIDER_MODE 값에 따라 provider 인스턴스 반환.

    - mock    : MockDataProvider (JSON 파일, 개발/테스트용)
    - fmp     : FMPDataProvider (Financial Modeling Prep API)
    - yfinance: YFinanceDataProvider (yfinance 라이브러리, 가격 데이터 전용)
    - hybrid  : HybridDataProvider (yfinance 가격 + FMP 컨센서스/어닝)
    """
    mode = settings.DATA_PROVIDER_MODE.lower().strip()

    if mode == "fmp":
        from app.services.provider.fmp_provider import FMPDataProvider
        return FMPDataProvider(api_key=settings.FMP_API_KEY)

    if mode == "yfinance":
        from app.services.provider.yfinance_provider import YFinanceDataProvider
        return YFinanceDataProvider()

    if mode == "hybrid":
        from app.services.provider.hybrid_provider import HybridDataProvider
        return HybridDataProvider(fmp_api_key=settings.FMP_API_KEY)

    # default: mock
    from app.services.provider.mock_provider import mock_provider
    return mock_provider
