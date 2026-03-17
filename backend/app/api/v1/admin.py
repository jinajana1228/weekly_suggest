"""Admin API — review task / item 관리

보호 방식:
  ADMIN_API_KEY 환경변수가 설정된 경우,
  모든 Admin 엔드포인트는 요청 헤더 `X-Admin-Key: <키>` 를 요구한다.
  빈 값이면 인증 없음 (로컬 개발용).
"""
from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.storage.file_store import file_store
from app.storage.state_store import state_store

router = APIRouter()


# ── Admin 인증 dependency ─────────────────────────────────────

def require_admin(x_admin_key: str | None = Header(None, alias="X-Admin-Key")):
    """ADMIN_API_KEY 가 설정된 환경에서만 키 검증."""
    if settings.ADMIN_API_KEY and x_admin_key != settings.ADMIN_API_KEY:
        raise HTTPException(status_code=403, detail="Admin access denied.")


# ── 요청 모델 ─────────────────────────────────────────────────

class ReviewItemUpdate(BaseModel):
    status: str          # PENDING | APPROVED | FLAGGED | REJECTED
    notes: str | None = None


class TaskDecisionRequest(BaseModel):
    decision: str        # APPROVE | REJECT | HOLD
    decided_by: str = "editor_01"
    reason: str | None = None


# ── DB 시드 (앱 시작 시 자동 호출) ───────────────────────────

def _ensure_seeded() -> None:
    """DB가 비어있으면 file_store mock 데이터로 시드."""
    mock_tasks = file_store.get_review_tasks()
    state_store.seed_from_mock(mock_tasks)


# ── 엔드포인트 ────────────────────────────────────────────────

@router.get("/admin/review-tasks", dependencies=[Depends(require_admin)])
async def get_review_tasks():
    """검토 작업 목록 반환 (SQLite 우선, fallback → mock)"""
    _ensure_seeded()
    tasks = state_store.get_all_tasks()
    if not tasks:
        tasks = file_store.get_review_tasks()
    return {"data": tasks}


@router.get("/admin/review-tasks/{task_id}", dependencies=[Depends(require_admin)])
async def get_review_task(task_id: str):
    """특정 검토 작업 상세 반환"""
    _ensure_seeded()
    task = state_store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="태스크를 찾을 수 없습니다.")
    return {"data": task}


@router.patch(
    "/admin/review-tasks/{task_id}/items/{item_id}",
    dependencies=[Depends(require_admin)],
)
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


@router.post(
    "/admin/review-tasks/{task_id}/decision",
    dependencies=[Depends(require_admin)],
)
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
