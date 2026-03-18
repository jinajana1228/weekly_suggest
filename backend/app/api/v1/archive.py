from fastapi import APIRouter, HTTPException
from app.storage.file_store import file_store

router = APIRouter()


@router.get("/archive")
async def get_archive():
    """전체 발행 이력 목록 반환"""
    editions = file_store.get_all_editions()
    summaries = []
    for e in editions:
        summaries.append({
            "report_id": e.get("report_id"),
            "edition_number": e.get("edition_number"),
            "issue_type": e.get("issue_type"),
            "status": e.get("status"),
            "published_at": e.get("published_at"),
            "data_as_of": e.get("data_as_of"),
            "market_context_note": e.get("market_context_note"),
            "stock_count": len(e.get("stocks", [])),
            "stocks": [
                {
                    "ticker": s.get("ticker"),
                    "company_name": s.get("company_name"),
                    "sector": s.get("sector"),
                    "one_line_thesis": s.get("one_line_thesis"),
                    "risk_level_overall": s.get("risk_level_overall"),
                    "valuation_signal": s.get("valuation_signal"),
                    "catalyst_badges": s.get("catalyst_badges"),
                    "report_item_id": s.get("report_item_id"),
                    "selection_type": s.get("selection_type"),
                }
                for s in e.get("stocks", [])
            ],
        })
    return {"data": summaries}


@router.get("/archive/{edition_number}")
async def get_archive_edition(edition_number: int):
    """특정 에디션 반환"""
    edition = file_store.get_edition_by_number(edition_number)
    if not edition:
        raise HTTPException(status_code=404, detail=f"에디션 {edition_number}을 찾을 수 없습니다.")
    return {"data": edition}
