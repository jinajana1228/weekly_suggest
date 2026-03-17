#!/usr/bin/env python3
"""
스크리닝 결과로 review task 생성 + SQLite에 저장.

실행 방법:
    cd weekly_suggest
    python scripts/create_review_task.py

    # 특정 리포트 ID 지정:
    python scripts/create_review_task.py --report-id re_20250317_002
"""
import sys
import uuid
import json
import argparse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.screening.pipeline import run_screening
from app.services.provider.mock_provider import mock_provider
from app.storage.state_store import state_store
from app.storage.file_store import file_store


def main():
    parser = argparse.ArgumentParser(description="Review Task 생성")
    parser.add_argument("--report-id", default="re_20250317_002", help="리포트 ID")
    parser.add_argument("--assignee", default="editor_01", help="담당자")
    args = parser.parse_args()

    print("=" * 60)
    print("Weekly Suggest: Review Task 생성")
    print("=" * 60)

    # 1) 스크리닝 실행
    print("\n[1/3] 스크리닝 실행 중...")
    screening = run_screening(mock_provider, use_mock_universe=True)
    print(f"      → {screening['selected_count']}개 종목 선정")

    # 2) review_task 구성
    task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    selected_tickers = [s["ticker"] for s in screening["selected"]]

    review_items = []
    for ticker in selected_tickers:
        item_id = f"ri_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{args.report_id.split('_')[-1]}_{ticker}"
        review_items.append({
            "report_item_id": item_id,
            "ticker": ticker,
            "review_status": "PENDING",
            "reviewer_notes": None,
            "data_quality_flag_count": 0,
            "llm_narrative_approved": False,
        })

    task = {
        "review_task_id": task_id,
        "report_id": args.report_id,
        "status": "OPEN",
        "assigned_to": args.assignee,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "screening_summary": screening["screening_summary"],
        "review_items": review_items,
        "publish_decision": None,
    }

    # 3) SQLite에 저장
    print(f"\n[2/3] SQLite에 task 저장 중... (ID: {task_id})")
    state_store.upsert_task(task)
    print("      → 저장 완료")

    # 4) 확인
    print(f"\n[3/3] 저장된 태스크 확인:")
    saved = state_store.get_task(task_id)
    if saved:
        print(f"      Task ID  : {saved['review_task_id']}")
        print(f"      Status   : {saved['status']}")
        print(f"      Items    : {len(saved['review_items'])}개 ({', '.join(i['ticker'] for i in saved['review_items'])})")
    else:
        print("      오류: 저장된 태스크를 찾을 수 없습니다.")

    print(f"\nDB 경로: {Path(__file__).parent.parent / 'data' / 'state.db'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
