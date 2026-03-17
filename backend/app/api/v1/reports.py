from fastapi import APIRouter, HTTPException
from app.storage.file_store import file_store
from app.storage.state_store import state_store

router = APIRouter()


@router.get("/reports/latest")
async def get_latest_report():
    """최신 PUBLISHED 에디션 반환.

    우선순위:
    1. SQLite latest_pointer → PUBLISHED 에디션 report_id로 JSON 조회
    2. fallback: edition_latest.json (초기 mock 상태용)
    """
    pointer = state_store.get_latest_pointer()
    if pointer:
        edition = file_store.get_edition_by_id(pointer)
        if edition:
            return {"data": edition}

    # fallback: mock 초기 상태 (pointer 미설정)
    edition = file_store.get_latest_edition()
    if not edition:
        raise HTTPException(status_code=404, detail="최신 리포트를 찾을 수 없습니다.")
    return {"data": edition}


@router.get("/reports/{report_id}/stocks/{ticker}")
async def get_stock_report(report_id: str, ticker: str):
    """특정 종목 상세 리포트 반환"""
    report = file_store.get_stock_report(ticker, report_id)
    if not report:
        raise HTTPException(
            status_code=404,
            detail=f"종목 {ticker}의 리포트를 찾을 수 없습니다."
        )
    return {"data": report}
