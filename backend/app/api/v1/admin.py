"""Admin API — review task / item 관리 + staging 검토 현황

보호 방식:
  ADMIN_API_KEY 환경변수가 설정된 경우,
  모든 Admin 엔드포인트는 요청 헤더 `X-Admin-Key: <키>` 를 요구한다.
  빈 값이면 인증 없음 (로컬 개발용).

인증 적용 방식:
  router.py 의 include_router(admin.router, dependencies=[Depends(require_admin)]) 로
  최외곽 include 단계에서 일괄 강제한다.
  이 방식은 FastAPI 버전과 무관하게 route table 반영이 보장된다.
"""
import json
import logging
import os
from pathlib import Path

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel

from app.core.config import settings
from app.services.screening.pipeline import run_screening
from app.services.provider.factory import get_provider
from app.storage.file_store import file_store
from app.storage.state_store import state_store

logger = logging.getLogger("weekly_suggest.admin")

# ── 모듈 수준 상수 ─────────────────────────────────────────────

_NARRATIVE_BLOCKS = (
    "why_discounted", "why_worth_revisiting",
    "key_risks_narrative", "investment_context",
)


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


class NarrativeBlockUpdate(BaseModel):
    block: str
    content: str
    approve: bool = False
    reviewer: str = "admin_ui"


# ── Staging 헬퍼 ──────────────────────────────────────────────

def _staging_file(ticker: str) -> Path | None:
    """staging 디렉토리에서 ticker 파일을 찾아 반환. 없으면 None."""
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    staging_dir  = project_root / "data" / "staging"
    if not staging_dir.exists():
        return None
    return next(
        (f for f in staging_dir.glob(f"*{ticker.upper()}*.json")
         if not f.name.startswith("edition_")),
        None,
    )


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


@router.get("/admin/staging/preflight")
async def get_staging_preflight():
    """staging 파일 기준 발행 전 상태 점검.

    CLI preflight 와 동일한 항목을 서버 측에서 재실행해 JSON으로 반환.
    Admin UI PreflightPanel 에서 소비한다.

    체크 항목 (종목별):
      [1] 차트 파일 존재 + price_series 유효 + interest_range_band 스키마
      [2] analyst_style_summary 4개 블록 완성도
      [3] selection_type 존재 + 유효 값 여부
      [4] placeholder / 미완성 마커 잔존 여부
    """
    from datetime import datetime, timezone

    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    staging_dir  = project_root / "data" / "staging"
    chart_dir    = project_root / "data" / "mock" / "chart"

    _PLACEHOLDER_MARKERS   = ("[운영자 작성 필요]", "[TODO]", "[TBD]")
    _VALID_SELECTION_TYPES = {"GROWTH_TRAJECTORY", "UNDERVALUED"}

    checked_at = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    if not staging_dir.exists():
        return {"data": {
            "staging_dir_exists": False,
            "checked_at": checked_at,
            "summary": {"total": 0, "ok_count": 0, "warn_count": 0,
                        "error_count": 0, "publishable": False},
            "tickers": [],
        }}

    stock_files = sorted(
        f for f in staging_dir.glob("*.json")
        if not f.name.startswith("edition_")
    )

    tickers_result = []

    for fpath in stock_files:
        checks: list = []

        try:
            raw_text = fpath.read_text(encoding="utf-8")
            data     = json.loads(raw_text)
        except Exception as e:
            tickers_result.append({
                "ticker":  fpath.stem,
                "overall": "ERROR",
                "checks":  [{"id": "parse", "label": "파일 읽기",
                              "status": "ERROR", "detail": str(e)}],
            })
            continue

        ticker = data.get("ticker", fpath.stem).upper()

        # ── [1] 차트 파일 ─────────────────────────────────────
        chart_path = chart_dir / f"{ticker}_price_series.json"
        if not chart_path.exists():
            checks.append({"id": "chart", "label": "차트 파일", "status": "ERROR",
                           "detail": f"{ticker}_price_series.json 없음"})
        else:
            try:
                cd         = json.loads(chart_path.read_text(encoding="utf-8"))
                raw_series = cd.get("data", cd.get("price_series", []))
                series_len = len(raw_series)
                if series_len == 0:
                    checks.append({"id": "chart", "label": "차트 파일", "status": "ERROR",
                                   "detail": "price_series 비어 있음"})
                else:
                    irb = cd.get("interest_range_band")
                    if irb is not None:
                        has_std = "lower_bound" in irb and "upper_bound" in irb
                        has_old = "low" in irb or "high" in irb
                        if not has_std and has_old:
                            checks.append({"id": "chart", "label": "차트 파일", "status": "ERROR",
                                           "detail": "irb 스키마 불일치 (low/high → lower/upper_bound 필요)"})
                        else:
                            checks.append({"id": "chart", "label": "차트 파일", "status": "OK",
                                           "detail": f"series={series_len}"})
                    else:
                        checks.append({"id": "chart", "label": "차트 파일", "status": "OK",
                                       "detail": f"series={series_len}  irb=없음"})
            except Exception as e:
                checks.append({"id": "chart", "label": "차트 파일", "status": "ERROR",
                               "detail": f"읽기 오류: {e}"})

        # ── [2] Narrative ─────────────────────────────────────
        asm = data.get("analyst_style_summary", {})
        if not asm:
            checks.append({"id": "narrative", "label": "Narrative", "status": "WARN",
                           "detail": "analyst_style_summary 없음 — narrate 실행 필요"})
        else:
            approved = missing = draft = 0
            for blk in _NARRATIVE_BLOCKS:
                blk_data = asm.get(blk, {})
                st       = blk_data.get("status", "")
                content  = blk_data.get("content", "")
                if st == "APPROVED":
                    approved += 1
                elif st == "DRAFT" and content:
                    draft += 1
                else:
                    missing += 1

            if missing > 0:
                checks.append({"id": "narrative", "label": "Narrative", "status": "ERROR",
                               "detail": f"{missing}개 블록 미완성  {approved}/4 APPROVED"})
            elif draft > 0:
                checks.append({"id": "narrative", "label": "Narrative", "status": "WARN",
                               "detail": f"{approved}/4 APPROVED  {draft}개 DRAFT 검토 필요"})
            else:
                checks.append({"id": "narrative", "label": "Narrative", "status": "OK",
                               "detail": "4/4 APPROVED"})

        # ── [3] selection_type ────────────────────────────────
        sel = data.get("selection_type", "")
        if not sel:
            checks.append({"id": "selection_type", "label": "선정 유형", "status": "ERROR",
                           "detail": "selection_type 없음"})
        elif sel not in _VALID_SELECTION_TYPES:
            checks.append({"id": "selection_type", "label": "선정 유형", "status": "ERROR",
                           "detail": f"잘못된 값: {sel!r}"})
        else:
            checks.append({"id": "selection_type", "label": "선정 유형", "status": "OK",
                           "detail": sel})

        # ── [4] 미완성 마커 ───────────────────────────────────
        found = [m for m in _PLACEHOLDER_MARKERS if m in raw_text]
        if data.get("financials", {}).get("status") == "UNAVAILABLE":
            found.append("financials=UNAVAILABLE")
        if "PLACEHOLDER" in raw_text:
            found.append("PLACEHOLDER 마커")

        if found:
            checks.append({"id": "placeholder", "label": "미완성 마커", "status": "WARN",
                           "detail": "  ".join(found[:3])})
        else:
            checks.append({"id": "placeholder", "label": "미완성 마커", "status": "OK",
                           "detail": "없음"})

        # ── overall 판정 ──────────────────────────────────────
        statuses = [c["status"] for c in checks]
        overall  = "ERROR" if "ERROR" in statuses else "WARN" if "WARN" in statuses else "OK"

        tickers_result.append({"ticker": ticker, "overall": overall, "checks": checks})

    ok_count    = sum(1 for t in tickers_result if t["overall"] == "OK")
    warn_count  = sum(1 for t in tickers_result if t["overall"] == "WARN")
    error_count = sum(1 for t in tickers_result if t["overall"] == "ERROR")
    publishable = error_count == 0 and len(tickers_result) > 0

    return {"data": {
        "staging_dir_exists": True,
        "checked_at":  checked_at,
        "summary": {
            "total":       len(tickers_result),
            "ok_count":    ok_count,
            "warn_count":  warn_count,
            "error_count": error_count,
            "publishable": publishable,
        },
        "tickers": tickers_result,
    }}


@router.get("/admin/staging/review-status")
async def get_staging_review_status():
    """staging draft 파일들의 narrative 검토 상태 반환.

    data/staging/ 디렉토리의 각 종목 파일에서
    analyst_style_summary 4개 블록의 status 와 reviewer_approved 를 읽어 반환한다.
    Admin UI의 StagingDraftPanel 에서 소비한다.
    """
    # admin.py = weekly_suggest/backend/app/api/v1/admin.py → parent×5 → weekly_suggest/
    project_root = Path(__file__).resolve().parent.parent.parent.parent.parent
    staging_dir  = project_root / "data" / "staging"

    if not staging_dir.exists():
        return {"data": {
            "staging_dir_exists": False,
            "draft_count":  0,
            "ready_count":  0,
            "tickers":      [],
        }}

    tickers = []
    for fpath in sorted(staging_dir.glob("*.json")):
        if fpath.name.startswith("edition_"):
            continue
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
            ticker = data.get("ticker", fpath.stem)
            asm    = data.get("analyst_style_summary", {})
            pm     = data.get("publication_meta", {})

            blocks = {
                blk: asm.get(blk, {}).get("status", "MISSING")
                for blk in _NARRATIVE_BLOCKS
            }
            all_approved = all(s == "APPROVED" for s in blocks.values())

            tickers.append({
                "ticker":                  ticker,
                "file":                    fpath.name,
                "reviewer_approved":       bool(asm.get("reviewer_approved", False)),
                "reviewed_by":             pm.get("reviewed_by"),
                "reviewed_at":             pm.get("reviewed_at"),
                "publication_meta_status": pm.get("status", "DRAFT"),
                "narrative_blocks":        blocks,
                "all_approved":            all_approved,
                "model_id":                asm.get("model_id", ""),
            })
        except Exception:
            pass

    ready_count = sum(1 for t in tickers if t["all_approved"])

    return {"data": {
        "staging_dir_exists": True,
        "draft_count":        len(tickers),
        "ready_count":        ready_count,
        "tickers":            tickers,
    }}


@router.post("/admin/staging/{ticker}/approve-narrative")
async def approve_staging_narrative(ticker: str):
    """staging draft 파일의 narrative 블록을 모두 APPROVED 로 표시.

    CLI review --approve-all 과 동일한 효과. Admin UI에서 종목별 승인 버튼으로 사용.
    """
    ticker = ticker.upper()
    fpath  = _staging_file(ticker)
    if not fpath:
        raise HTTPException(status_code=404, detail=f"staging 파일 없음: {ticker}")

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    asm = data.get("analyst_style_summary", {})
    if not asm:
        raise HTTPException(status_code=422, detail="analyst_style_summary 없음 -- narrate 먼저 실행")

    changed = False
    for blk in _NARRATIVE_BLOCKS:
        blk_data = asm.get(blk, {})
        if blk_data.get("status") != "APPROVED" and blk_data.get("content", ""):
            asm[blk]["status"] = "APPROVED"
            changed = True

    all_approved = all(asm.get(b, {}).get("status") == "APPROVED" for b in _NARRATIVE_BLOCKS)
    asm["reviewer_approved"] = all_approved

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pm = data.get("publication_meta", {})
    pm["reviewed_by"]     = "admin_ui"
    pm["reviewed_at"]     = now_iso
    pm["last_updated_at"] = now_iso

    data["analyst_style_summary"] = asm
    data["publication_meta"]      = pm

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"data": {
        "ticker":       ticker,
        "changed":      changed,
        "all_approved": all_approved,
        "reviewed_by":  pm["reviewed_by"],
    }}


@router.get("/admin/staging/{ticker}/narrative")
async def get_staging_narrative(ticker: str):
    """staging draft 파일의 narrative 블록 내용 반환.

    Admin UI StagingTickerCard 에서 편집 패널 열 때 호출.
    blocks: {block_key: {content, status}} 형태로 4개 블록 반환.
    """
    fpath = _staging_file(ticker.upper())
    if not fpath:
        raise HTTPException(status_code=404, detail=f"staging 파일 없음: {ticker}")

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    asm = data.get("analyst_style_summary", {})
    if not asm:
        raise HTTPException(
            status_code=422, detail="analyst_style_summary 없음 -- narrate 먼저 실행"
        )

    blocks = {
        blk: {
            "content": asm.get(blk, {}).get("content", ""),
            "status":  asm.get(blk, {}).get("status", "MISSING"),
        }
        for blk in _NARRATIVE_BLOCKS
    }

    return {"data": {
        "ticker":            ticker.upper(),
        "blocks":            blocks,
        "reviewer_approved": bool(asm.get("reviewer_approved", False)),
        "model_id":          asm.get("model_id", ""),
    }}


@router.patch("/admin/staging/{ticker}/narrative")
async def patch_staging_narrative(ticker: str, body: NarrativeBlockUpdate):
    """staging draft 파일의 단일 narrative 블록 내용 수정 (+ 선택적 승인).

    body.approve=True 이면 해당 블록 status → APPROVED.
    4개 블록 모두 APPROVED 이면 reviewer_approved=True 자동 설정.
    """
    if body.block not in _NARRATIVE_BLOCKS:
        raise HTTPException(
            status_code=422,
            detail=f"block must be one of {_NARRATIVE_BLOCKS}",
        )

    fpath = _staging_file(ticker.upper())
    if not fpath:
        raise HTTPException(status_code=404, detail=f"staging 파일 없음: {ticker}")

    with open(fpath, "r", encoding="utf-8") as f:
        data = json.load(f)

    asm = data.get("analyst_style_summary", {})
    if not asm:
        raise HTTPException(
            status_code=422, detail="analyst_style_summary 없음 -- narrate 먼저 실행"
        )

    blk_data = asm.get(body.block, {})
    blk_data["content"] = body.content
    if body.approve:
        blk_data["status"] = "APPROVED"
    elif blk_data.get("status") != "APPROVED":
        blk_data["status"] = "DRAFT"
    asm[body.block] = blk_data

    all_approved = all(
        asm.get(b, {}).get("status") == "APPROVED" for b in _NARRATIVE_BLOCKS
    )
    asm["reviewer_approved"] = all_approved

    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    pm = data.get("publication_meta", {})
    pm["last_updated_at"] = now_iso
    if body.approve:
        pm["reviewed_by"] = body.reviewer
        pm["reviewed_at"] = now_iso

    data["analyst_style_summary"] = asm
    data["publication_meta"]      = pm

    with open(fpath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    return {"data": {
        "ticker":            ticker.upper(),
        "block":             body.block,
        "status":            blk_data["status"],
        "reviewer_approved": all_approved,
    }}


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
