import logging
import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.api.v1.router import api_router

# ── 로깅 설정 ─────────────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger("weekly_suggest")

# ── FastAPI 앱 ─────────────────────────────────────────────────
# 프로덕션 환경에서는 Swagger/ReDoc UI를 비활성화한다.
app = FastAPI(
    title="Weekly Suggest API",
    description="미국 상장 중대형주 저평가 리포트 서비스 API",
    version="0.2.0",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.on_event("startup")
async def _startup():
    # 진단 로그: Railway 환경변수 주입 여부 직접 확인
    logger.info("DIAG os.getenv('APP_ENV') = %r", os.getenv("APP_ENV"))
    logger.info("DIAG settings.APP_ENV     = %r", settings.APP_ENV)
    logger.info(
        "Weekly Suggest API starting | env=%s | provider=%s",
        settings.APP_ENV,
        settings.DATA_PROVIDER_MODE,
    )
    _validate_config()


def _validate_config() -> None:
    """시작 시 환경변수 설정을 검증하고 잘못된 설정을 경고한다."""
    mode = settings.DATA_PROVIDER_MODE.lower().strip()

    if settings.is_production:
        if not settings.ADMIN_API_KEY:
            logger.warning(
                "SECURITY WARNING: ADMIN_API_KEY is not set in production. "
                "Admin endpoints are unprotected. Set ADMIN_API_KEY in Railway Variables."
            )
        if "localhost" in settings.CORS_ORIGINS:
            logger.warning(
                "CONFIG WARNING: CORS_ORIGINS contains 'localhost' in production. "
                "Set CORS_ORIGINS to your Vercel domain in Railway Variables."
            )

    if mode in ("fmp", "hybrid") and not settings.FMP_API_KEY:
        logger.error(
            "CONFIG ERROR: DATA_PROVIDER_MODE=%s requires FMP_API_KEY but it is not set. "
            "Provider will fail on first use. Set FMP_API_KEY in Railway Variables.",
            mode,
        )

    if mode not in ("mock", "fmp", "yfinance", "hybrid"):
        logger.error(
            "CONFIG ERROR: Unknown DATA_PROVIDER_MODE=%s. "
            "Falling back to mock. Valid values: mock | fmp | yfinance | hybrid",
            mode,
        )


@app.get("/health")
async def health_check():
    # os.getenv 직접 읽기 — pydantic-settings 싱글턴을 거치지 않고
    # 런타임 환경변수를 즉시 반환한다. settings 캐싱 문제 방어.
    return {
        "status": "ok",
        "env": os.getenv("APP_ENV", settings.APP_ENV),
        "provider_mode": os.getenv("DATA_PROVIDER_MODE", settings.DATA_PROVIDER_MODE),
        "version": "0.2.0",
        "build": "20260317-1",   # 이 값이 응답에 보이면 신규 코드가 서빙 중임을 확인
    }
