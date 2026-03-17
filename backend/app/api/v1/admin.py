"""Admin API — review task / item 관리

보호 방식:
  ADMIN_API_KEY 환경변수가 설정된 경우,
  모든 Admin 엔드포인트는 요청 헤더 `X-Admin-Key: <키>` 를 요구한다.
  빈 값이면 인증 없음 (로컬 개발용).

인증 적용 방식:
  router.py 의 include_router(admin.router, dependencies=[Depends(require_admin)]) 로
  최외곽 include 단계에서 일괄 강제한다.
  이 방식은 FastAPI 버전과 무관하게 route table 반영이 보장된다.
"""
import logging
import os

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.screening.pipeline import run_screening
from app.services.provider.factory import get_provider
from app.storage.file_store import file_store
from app.storage.state_store import state_store

logger = logging.getLogger("weekly_suggest.admin")


# ── Admin 인증 dependency ─────────────────────────────────────

def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    """ADMIN_API_KEY 가 설정된 환경에서만 키 검증.

    os.getenv()를 요청 시점에 직접 호출 — Railway 환경변수 주입 타이밍 문제 우회.
    진단 로그가 Railway Deploy Logs에 찍히면 dependency가 정상 호출됨을 확인할 수 있다.
    """
    admin_key = os.getenv("ADMIN_API_KEY") or settings.ADMIN_API_KEY

    # 진단 로그 — Railway 로그에서 호출 여부 + key 설정 여부 확인용
    logger.warning(
        "ADMIN_AUTH diag: key_set=%r header_present=%r",
        bool(admin_key),
        bool(x_admin_key),
    )

    if admin_key and x_admin_key != admin_key:
        raise HTTPException(status_code=403, detail="Admin access denied.")


# ── 라우터 (dependency는 router.py include_router 단계에서 적용) ──
router = APIRouter()


# ── 요청 모델 ─────────────────────────────────────────────────

class ReviewItemUpdate(BaseModel):
    status: str          # PENDING | APPROVED | FLAGGED | REJECTED
    notes: str | None = None


class TaskDecisionRequest(BaseModel):
    decision: str        # APPROVE | REJECT | HOLD
    decided_by: str = "editor_01"
    reason: str | None = None


class ScreeningRequest(BaseModel):
    min_market_cap_usd_b: float = 2.0
    require_operating_income: bool = True
    exclude_adr: bool = True
    exclude_bankruptcy: bool = True
    top_n: int = 5


# ── DB 시드 (앱 시작 시 자동 호출) ───────────────────────────

def _ensure_seeded() -> None:
    """DB가 비어있으면 file_store mock 데이터로 시드."""
    mock_tasks = file_store.get_review_tasks()
    state_store.seed_from_mock(mock_tasks)


# ── 엔드포인트 ────────────────────────────────────────────────

@router.get("/admin/review-tasks")
async def get_review_tasks():
    """검토 작업 목록 반환 (SQLite 우선, fallback → mock)"""
    _ensure_seeded()
    tasks = state_store.get_all_tasks()
    if not tasks:
        tasks = file_store.get_review_tasks()
    return {"data": tasks}


@router.get("/admin/review-tasks/{task_id}")
async def get_review_task(task_id: str):
    """특정 검토 작업 상세 반환"""
    _ensure_seeded()
    task = state_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
    return {"data": task}


@router.patch("/admin/review-tasks/{task_id}/items/{item_id}")
async def update_review_item(
    task_id: str,
    item_id: str,
    body: ReviewItemUpdate,
):
    """리뷰 아이템 상태 변경 (PENDING / APPROVED / FLAGGED / REJECTED)"""
    allowed = {"PENDING", "APPROVED", "FLAGGED", "REJECTED"}
    if body.status not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"status must be one of {allowed}",
        )
    _ensure_seeded()
    updated = state_store.update_review_item(task_id, item_id, body.status, body.notes)
    if not updated:
        raise HTTPException(status_code=404, detail="아이템을 찾을 수 없습니다.")

    task = state_store.get_task(task_id)
    return {"data": task}


@router.post("/admin/review-tasks/{task_id}/decision")
async def set_task_decision(task_id: str, body: TaskDecisionRequest):
    """태스크 발행 결정 (APPROVE / REJECT / HOLD)"""
    allowed = {"APPROVE", "REJECT", "HOLD"}
    if body.decision not in allowed:
        raise HTTPException(
            status_code=422,
            detail=f"decision must be one of {allowed}",
        )
    _ensure_seeded()
    updated = state_store.set_task_decision(
        task_id, body.decision, body.decided_by, body.reason
    )
    if not updated:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")

    if body.decision == "APPROVE":
        task = state_store.get_task(task_id)
        if task:
            report_id = task["report_id"]
            state_store.update_edition_status(report_id, "PUBLISHED")
            state_store.set_latest_pointer(report_id, body.decided_by)

    task = state_store.get_task(task_id)
    return {"data": task}


@router.post("/admin/screening/run")
async def run_screening_endpoint(body: ScreeningRequest | None = None):
    """
    스크리닝 파이프라인 1회 실행 (Admin 전용).
    DATA_PROVIDER_MODE=mock이면 mock universe, 실데이터 모드면 실제 screener 사용.
    """
    filters = body.model_dump() if body else {}
    top_n = filters.pop("top_n", 5)
    use_mock = settings.DATA_PROVIDER_MODE.lower() == "mock"

    result = run_screening(
        provider=get_provider(),
        filters=filters,
        top_n=top_n,
        use_mock_universe=use_mock,
    )
    return {"data": result}
