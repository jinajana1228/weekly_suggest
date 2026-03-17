#!/usr/bin/env python3
"""
새 에디션 생성 — 스크리닝 실행 + review task + editions 테이블 등록.

실행 방법:
    cd weekly_suggest
    python scripts/create_edition.py

    # 발행 유형 지정:
    python scripts/create_edition.py --issue-type EARNINGS_TRIGGERED --assignee editor_01

    # 드라이런 (DB 변경 없음):
    python scripts/create_edition.py --dry-run
"""
import sys
import uuid
import argparse
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.screening.pipeline import run_screening
from app.services.provider.mock_provider import mock_provider
from app.storage.state_store import state_store


VALID_ISSUE_TYPES = {"REGULAR_BIWEEKLY", "EARNINGS_TRIGGERED", "SPECIAL_EVENT"}


def main():
    parser = argparse.ArgumentParser(description="새 에디션 생성")
    parser.add_argument("--issue-type", default="REGULAR_BIWEEKLY",
                        choices=list(VALID_ISSUE_TYPES), help="발행 유형")
    parser.add_argument("--assignee", default="editor_01", help="검토 담당자")
    parser.add_argument("--top-n", type=int, default=5, help="최종 선정 종목 수")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 흐름만 확인")
    args = parser.parse_args()

    dry = args.dry_run
    prefix = "[DRY-RUN] " if dry else ""

    print("=" * 62)
    print(f"{prefix}Weekly Suggest: 새 에디션 생성")
    print(f"  발행 유형 : {args.issue_type}")
    print(f"  담당자    : {args.assignee}")
    if dry:
        print("  ※ DRY-RUN 모드: DB에 변경사항 없음")
    print("=" * 62)

    # 1) 스크리닝
    print("\n[1/4] 스크리닝 실행 중...")
    screening = run_screening(mock_provider, top_n=args.top_n, use_mock_universe=True)
    print(f"      후보 {screening['total_candidates']}개 -> 선정 {screening['selected_count']}개")
    for s in screening["selected"]:
        print(f"        {s['ticker']:6s} score={s['score']:.1f}  "
              f"discount={s['sector_discount_pct']:.1f}%  "
              f"risk={s['risk_level_max']}")

    # 2) 에디션 번호 결정
    print("\n[2/4] 에디션 번호 결정...")
    if dry:
        next_num = state_store.get_next_edition_number()
        print(f"      다음 에디션 번호 (예상): {next_num}")
    else:
        next_num = state_store.get_next_edition_number()
        print(f"      에디션 번호: {next_num}")

    now_str = datetime.now(timezone.utc).strftime("%Y%m%d")
    report_id = f"re_{now_str}_{next_num:03d}"
    print(f"      report_id : {report_id}")

    # 3) review task 구성
    print("\n[3/4] Review Task 구성...")
    task_id = f"task_{now_str}_{uuid.uuid4().hex[:6]}"
    data_as_of = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    review_items = [
        {
            "report_item_id": f"ri_{now_str}_{next_num:03d}_{s['ticker']}",
            "ticker": s["ticker"],
            "review_status": "PENDING",
            "reviewer_notes": None,
            "data_quality_flag_count": 0,
            "llm_narrative_approved": False,
        }
        for s in screening["selected"]
    ]
    task = {
        "review_task_id": task_id,
        "report_id": report_id,
        "status": "OPEN",
        "assigned_to": args.assignee,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "completed_at": None,
        "screening_summary": screening["screening_summary"],
        "review_items": review_items,
        "publish_decision": None,
    }

    print(f"      Task ID   : {task_id}")
    print(f"      종목      : {', '.join(i['ticker'] for i in review_items)}")

    if not dry:
        state_store.upsert_task(task)
        state_store.register_edition(
            report_id=report_id,
            edition_number=next_num,
            issue_type=args.issue_type,
            data_as_of=data_as_of,
        )
        print("      -> DB 저장 완료")

    # 4) 결과 확인
    print("\n[4/4] 생성 결과:")
    if not dry:
        saved = state_store.get_task(task_id)
        meta = state_store.get_edition_meta(report_id)
        if saved:
            print(f"      Task status    : {saved['status']}")
            print(f"      Task items     : {len(saved['review_items'])}개")
        if meta:
            print(f"      Edition number : VOL.{meta['edition_number']}")
            print(f"      Issue type     : {meta['issue_type']}")
            print(f"      Data as of     : {meta['data_as_of']}")
    else:
        print("      (dry-run: DB 상태 확인 생략)")

    print()
    print("=" * 62)
    print(f"{prefix}에디션 생성 완료")
    print(f"  report_id : {report_id}")
    print(f"  task_id   : {task_id}")
    print()
    print("다음 단계: 검토 후 아래 명령으로 발행")
    print(f"  python scripts/publish_edition.py --report-id {report_id} --task-id {task_id}")
    print("=" * 62)


if __name__ == "__main__":
    main()
