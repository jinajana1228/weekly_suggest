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
app = FastAPI(
    title="Weekly Suggest API",
    description="미국 상장 중대형주 저평가 리포트 서비스 API",
    version="0.2.0",
    docs_url=None,
    redoc_url=None,
    openapi_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")

# ── Startup 시점에 결정된 환경 값 ────────────────────────────
# settings = Settings()는 임포트 시점에 실행된다.
# Railway 환경변수 주입이 그 이후에 완료되는 경우,
# settings.APP_ENV가 기본값(development)으로 고정될 수 있다.
# _runtime_env는 startup 이벤트(환경변수 주입 완료 후)에서 캡처해
# health 엔드포인트가 항상 정확한 값을 반환하도록 보장한다.
_runtime_env: str = os.getenv("APP_ENV", settings.APP_ENV)
_runtime_provider: str = os.getenv("DATA_PROVIDER_MODE", settings.DATA_PROVIDER_MODE)


@app.on_event("startup")
async def _startup():
    global _runtime_env, _runtime_provider

    # startup 시점에 환경변수를 재캡처 (임포트 시점보다 늦게 주입된 경우 보정)
    _runtime_env = os.getenv("APP_ENV", settings.APP_ENV)
    _runtime_provider = os.getenv("DATA_PROVIDER_MODE", settings.DATA_PROVIDER_MODE)

    # 진단 로그
    logger.info("DIAG os.getenv('APP_ENV')      = %r", os.getenv("APP_ENV"))
    logger.info("DIAG settings.APP_ENV           = %r", settings.APP_ENV)
    logger.info("DIAG _runtime_env (캡처됨)      = %r", _runtime_env)
    logger.info(
        "Weekly Suggest API starting | env=%s | provider=%s",
        _runtime_env,
        _runtime_provider,
    )
    _validate_config()


def _validate_config() -> None:
    """시작 시 환경변수 설정을 검증하고 잘못된 설정을 경고한다."""
    mode = _runtime_provider.lower().strip()
    is_prod = _runtime_env.lower() == "production"

    if is_prod:
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
    # _runtime_env는 startup 이벤트에서 캡처된 값 — os.getenv 타이밍 문제 방어
    # diag 필드로 요청 시점 os.getenv와 settings 값을 함께 노출 (진단용)
    return {
        "status": "ok",
        "env": _runtime_env,
        "provider_mode": _runtime_provider,
        "version": "0.2.0",
        "build": "20260317-2",
        "diag_runtime": os.getenv("APP_ENV"),    # 요청 시점 os.getenv 직접 확인용
        "diag_settings": settings.APP_ENV,       # 요청 시점 settings 확인용
    }
