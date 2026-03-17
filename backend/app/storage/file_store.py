"""JSON 파일 기반 리포트 저장소"""
import json
import os
from pathlib import Path
from typing import Any, Optional

from app.core.config import settings


def _mock_data_dir() -> Path:
    """
    MOCK_DATA_DIR 환경변수를 절대경로로 해석.
    상대경로인 경우 __file__ 기준으로 해석 (CWD 독립).
    __file__ = backend/app/storage/file_store.py
    → parent×4 = weekly_suggest/
    → weekly_suggest/data/mock
    """
    configured = settings.MOCK_DATA_DIR
    p = Path(configured)
    if p.is_absolute():
        return p
    # 상대경로: weekly_suggest 루트 기준으로 해석
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    return (project_root / configured.lstrip("./")).resolve()


class FileStore:
    def __init__(self):
        self.base_dir = _mock_data_dir()

    def _read_json(self, relative_path: str) -> Optional[Any]:
        full_path = self.base_dir / relative_path
        if not full_path.exists():
            return None
        with open(full_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_latest_edition(self) -> Optional[dict]:
        return self._read_json("reports/edition_latest.json")

    def get_edition_by_number(self, edition_number: int) -> Optional[dict]:
        if edition_number == 2:
            return self._read_json("reports/edition_latest.json")
        return self._read_json(f"reports/edition_{edition_number:03d}_archive.json")

    def get_edition_by_id(self, report_id: str) -> Optional[dict]:
        """report_id로 에디션 JSON 반환.
        예: re_20250317_002 → edition_latest.json (edition 2)
             re_20250303_001 → edition_001_archive.json
        """
        # report_id 마지막 세그먼트가 에디션 번호
        try:
            edition_num = int(report_id.split("_")[-1])
        except (ValueError, IndexError):
            return None
        return self.get_edition_by_number(edition_num)

    def get_all_editions(self) -> list[dict]:
        results = []
        reports_dir = self.base_dir / "reports"
        if not reports_dir.exists():
            return results
        for fname in sorted(reports_dir.iterdir(), reverse=True):
            if fname.name.startswith("edition_") and fname.suffix == ".json":
                with open(fname, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    results.append(data)
        return results

    def get_stock_report(self, ticker: str, report_id: str) -> Optional[dict]:
        # report_id에서 에디션 번호 추출
        suffix = report_id.split("_")[-1]
        filename = f"reports/stock_{ticker.upper()}_{suffix}.json"
        result = self._read_json(filename)
        if result:
            return result
        # fallback: 최신 에디션에서 ticker 검색
        edition = self.get_latest_edition()
        if edition:
            for stock in edition.get("stocks", []):
                if stock.get("ticker") == ticker.upper():
                    # 개별 파일 재시도
                    for f in (self.base_dir / "reports").glob(f"stock_{ticker.upper()}_*.json"):
                        with open(f, "r", encoding="utf-8") as fp:
                            return json.load(fp)
        return None

    def get_chart_data(self, ticker: str) -> Optional[dict]:
        return self._read_json(f"chart/{ticker.upper()}_price_series.json")

    def get_review_tasks(self) -> list[dict]:
        """Mock 검토 태스크 반환"""
        return [
            {
                "review_task_id": "task_20250315_001",
                "report_id": "re_20250317_002",
                "status": "COMPLETED",
                "assigned_to": "editor_01",
                "created_at": "2025-03-15T08:00:00Z",
                "completed_at": "2025-03-15T13:00:00Z",
                "screening_summary": {
                    "total_candidates": 12,
                    "selected_count": 5,
                    "excluded_count": 7,
                    "run_at": "2025-03-15T07:30:00Z",
                    "filters_applied": ["market_cap_2b_plus", "avg_volume_10m_plus", "operating_income_positive", "no_adr", "no_bankruptcy"]
                },
                "review_items": [
                    {"report_item_id": "ri_20250317_002_MFGI", "ticker": "MFGI", "review_status": "APPROVED", "reviewer_notes": "분석 검토 완료. 수치 정합성 확인.", "data_quality_flag_count": 1, "llm_narrative_approved": True},
                    {"report_item_id": "ri_20250317_002_RVNC", "ticker": "RVNC", "review_status": "APPROVED", "reviewer_notes": "금융 섹터 P/B 기준 검토 완료.", "data_quality_flag_count": 0, "llm_narrative_approved": True},
                    {"report_item_id": "ri_20250317_002_HLTH", "ticker": "HLTH", "review_status": "APPROVED", "reviewer_notes": "Catalyst B 미확인 사항 플래그 확인 및 수용.", "data_quality_flag_count": 2, "llm_narrative_approved": True},
                    {"report_item_id": "ri_20250317_002_CSTM", "ticker": "CSTM", "review_status": "APPROVED", "reviewer_notes": "검토 완료.", "data_quality_flag_count": 0, "llm_narrative_approved": True},
                    {"report_item_id": "ri_20250317_002_ENXT", "ticker": "ENXT", "review_status": "APPROVED", "reviewer_notes": "에너지 고리스크 명시 확인.", "data_quality_flag_count": 1, "llm_narrative_approved": True}
                ],
                "publish_decision": {
                    "decision": "APPROVE",
                    "decided_by": "editor_01",
                    "decided_at": "2025-03-15T14:00:00Z",
                    "reason": None
                }
            }
        ]


file_store = FileStore()
