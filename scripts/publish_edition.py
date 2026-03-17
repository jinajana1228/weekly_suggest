#!/usr/bin/env python3
"""
에디션 발행 — publish guard 통과 후 latest_pointer 갱신.

실행 방법:
    cd weekly_suggest
    python scripts/publish_edition.py --report-id re_20250317_002 --task-id task_20250315_001

    # 드라이런 (DB 변경 없음):
    python scripts/publish_edition.py --report-id re_20250317_002 --task-id task_20250315_001 --dry-run

    # 이미 발행된 에디션 강제 재발행 (비권장):
    python scripts/publish_edition.py --report-id re_20250317_002 --task-id task_20250315_001 --allow-overwrite
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.storage.state_store import state_store
from app.services.publication.publish_guard import check_publish_guard


def main():
    parser = argparse.ArgumentParser(description="에디션 발행")
    parser.add_argument("--report-id", required=True, help="발행할 report_id")
    parser.add_argument("--task-id", required=True, help="연결된 review task_id")
    parser.add_argument("--decided-by", default="editor_01", help="발행 결정자")
    parser.add_argument("--reason", default=None, help="발행 사유 메모")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 흐름만 확인")
    parser.add_argument("--allow-overwrite", action="store_true",
                        help="이미 발행된 에디션도 재발행 허용")
    args = parser.parse_args()

    dry = args.dry_run
    prefix = "[DRY-RUN] " if dry else ""

    print("=" * 62)
    print(f"{prefix}Weekly Suggest: 에디션 발행")
    print(f"  report_id  : {args.report_id}")
    print(f"  task_id    : {args.task_id}")
    print(f"  decided_by : {args.decided_by}")
    if dry:
        print("  ※ DRY-RUN 모드: DB에 변경사항 없음")
    print("=" * 62)

    # Step 1: publish guard
    print("\n[1/3] Publish Guard 검사...")
    result = check_publish_guard(
        task_id=args.task_id,
        report_id=args.report_id,
        allow_overwrite=args.allow_overwrite,
    )

    if result.warnings:
        for w in result.warnings:
            print(f"  [WARN] {w}")

    if not result.can_publish:
        print("\n  발행 조건 미충족: 아래 문제를 해결 후 재실행하세요.")
        for issue in result.issues:
            print(f"  [BLOCK] {issue}")
        print("\n" + "=" * 62)
        print("발행 중단")
        print("=" * 62)
        sys.exit(1)

    print("  -> 발행 조건 충족 (모든 검사 통과)")

    # Step 2: 현재 상태 확인
    print("\n[2/3] 현재 상태 확인...")
    task = state_store.get_task(args.task_id)
    if task:
        items = task.get("review_items", [])
        print(f"  Task status   : {task['status']}")
        print(f"  Review items  : {len(items)}개 ({sum(1 for i in items if i['review_status'] == 'APPROVED')} APPROVED)")
        existing_decision = task.get("publish_decision")
        if existing_decision:
            print(f"  기존 결정     : {existing_decision.get('decision')} by {existing_decision.get('decided_by')}")

    current_latest = state_store.get_latest_pointer()
    print(f"  현재 latest   : {current_latest or '(없음)'}")
    edition_meta = state_store.get_edition_meta(args.report_id)
    if edition_meta:
        print(f"  에디션 번호   : VOL.{edition_meta['edition_number']} ({edition_meta['issue_type']})")

    # Step 3: 발행 실행
    print("\n[3/3] 발행 실행...")
    if not dry:
        state_store.set_task_decision(
            args.task_id, "APPROVE", args.decided_by, args.reason
        )
        state_store.update_edition_status(args.report_id, "PUBLISHED")
        state_store.set_latest_pointer(args.report_id, args.decided_by)

        new_latest = state_store.get_latest_pointer()
        print(f"  -> Task status    : COMPLETED")
        print(f"  -> Edition status : PUBLISHED")
        print(f"  -> latest_pointer : {new_latest}")
        print()
        print("  프론트엔드 메인 페이지(/)에서 새 에디션이 표시됩니다.")
    else:
        print("  (dry-run: DB 변경 생략)")
        print(f"  예상 결과: {args.report_id} -> PUBLISHED, latest_pointer 갱신")

    print()
    print("=" * 62)
    print(f"{prefix}발행 완료" if not dry else f"{prefix}드라이런 완료 (실제 발행 없음)")
    print("=" * 62)


if __name__ == "__main__":
    main()
