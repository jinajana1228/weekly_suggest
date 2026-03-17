from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # ── 실행 환경 ────────────────────────────────────────────────
    # 주의: 'ENV'는 POSIX 예약 변수 (shell이 /etc/profile 등으로 설정함)
    # Railway 등 컨테이너 환경에서 충돌을 피하기 위해 APP_ENV를 사용한다.
    APP_ENV: str = "development"      # development | production
    LOG_LEVEL: str = "INFO"

    # ── 데이터 제공자 ─────────────────────────────────────────────
    DATA_PROVIDER_MODE: str = "mock"  # mock | fmp | yfinance | hybrid
    MOCK_DATA_DIR: str = "../data/mock"
    FMP_API_KEY: str = ""

    # ── LLM Narrative ─────────────────────────────────────────────
    ANTHROPIC_API_KEY: str = ""
    NARRATIVE_MODEL: str = "claude-sonnet-4-6"
    NARRATIVE_REQUIRE_FOR_PUBLISH: bool = False

    # ── CORS ─────────────────────────────────────────────────────
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    # ── 발행 정책 ─────────────────────────────────────────────────
    MIN_PUBLISH_STOCKS: int = 5
    MAX_DATA_QUALITY_FLAGS: int = 3
    DATA_FRESHNESS_THRESHOLD_HOURS: int = 72

    # ── 스토리지 경로 오버라이드 ──────────────────────────────────
    # 빈 값이면 __file__ 기반 자동 해석 (로컬 개발 + Railway 표준 구조)
    # Railway Volume 사용 시: STATE_DB_PATH=/data/state.db
    STATE_DB_PATH: str = ""
    # 빈 값이면 __file__ 기반 + MOCK_DATA_DIR 설정값 사용
    # Railway Volume 사용 시: MOCK_DATA_DIR=/data/mock
    # (file_store.py에서 이미 절대경로 처리 지원)

    # ── Admin 보호 ────────────────────────────────────────────────
    # 비어있으면 인증 없음 (로컬 개발용).
    # 배포 시 반드시 설정: 임의의 긴 랜덤 문자열.
    # 요청 시 Header: X-Admin-Key: <값>
    ADMIN_API_KEY: str = ""

    @property
    def cors_origins_list(self) -> List[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
