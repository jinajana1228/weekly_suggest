#!/usr/bin/env python3
"""
샘플 publish flow 전체 실행 (스크리닝 → task 생성 → 검토 → 승인 → 발행).

실행 방법:
    cd weekly_suggest
    python scripts/publish_flow.py

    # 드라이런 (DB 변경 없이 흐름만 확인):
    python scripts/publish_flow.py --dry-run
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


def step(n: int, title: str, dry: bool = False) -> None:
    prefix = "[DRY-RUN] " if dry else ""
    print(f"\n[Step {n}] {prefix}{title}")
    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(description="Publish Flow 샘플 실행")
    parser.add_argument("--dry-run", action="store_true", help="DB 변경 없이 흐름만 출력")
    parser.add_argument("--report-id", default="re_20250317_002")
    args = parser.parse_args()

    print("=" * 60)
    print("Weekly Suggest: Publish Flow")
    print(f"Report ID: {args.report_id}")
    if args.dry_run:
        print("※ DRY-RUN 모드: DB에 변경사항 없음")
    print("=" * 60)

    # ── Step 1: 스크리닝 ──────────────────────────────────────
    step(1, "스크리닝 실행", args.dry_run)
    result = run_screening(mock_provider, use_mock_universe=True)
    selected = result["selected"]
    print(f"  후보 {result['total_candidates']}개 → 선정 {result['selected_count']}개")
    for s in selected:
        print(f"  ✓ {s['ticker']:6s} score={s['score']:.1f}")

    # ── Step 2: Review Task 생성 ──────────────────────────────
    step(2, "Review Task 생성", args.dry_run)
    task_id = f"task_{datetime.now(timezone.utc).strftime('%Y%m%d')}_{uuid.uuid4().hex[:6]}"
    review_items = [
        {
            "report_item_id": f"ri_{datetime.now(timezone.utc).strftime('%Y%m%d')}_"
                              f"{args.report_id.split('_')[-1]}_{s['ticker']}",
            "ticker": s["ticker"],
            "review_status": "PENDING",
            "reviewer_notes": None,
            "data_quality_flag_count": 0,
            "llm_narrative_approved": False,
        }
        for s in selected
    ]
    task = {
        "review_task_id": task_id,
        "report_id": args.report_id,
        "status": "OPEN",
        "assigned_to": "editor_01",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "screening_summary": result["screening_summary"],
        "review_items": review_items,
    }
    print(f"  Task ID: {task_id}")
    print(f"  종목: {', '.join(s['ticker'] for s in selected)}")
    if not args.dry_run:
        state_store.upsert_task(task)
        print("  → DB 저장 완료")

    # ── Step 3: 종목별 검토 (APPROVED) ───────────────────────
    step(3, "종목별 검토 상태 → APPROVED", args.dry_run)
    for item in review_items:
        ticker = item["ticker"]
        item_id = item["report_item_id"]
        print(f"  {ticker} → APPROVED")
        if not args.dry_run:
            state_store.update_review_item(task_id, item_id, "APPROVED", f"{ticker} 검토 완료")

    # ── Step 4: 발행 결정 → APPROVE ──────────────────────────
    step(4, "발행 결정 → APPROVE (발행)", args.dry_run)
    print(f"  결정: APPROVE by editor_01")
    if not args.dry_run:
        state_store.set_task_decision(task_id, "APPROVE", "editor_01")
        state_store.update_edition_status(args.report_id, "PUBLISHED")
        print(f"  → Task status: COMPLETED")
        print(f"  → Edition {args.report_id}: PUBLISHED")

    # ── Step 5: 결과 확인 ─────────────────────────────────────
    step(5, "최종 상태 확인", args.dry_run)
    if not args.dry_run:
        saved_task = state_store.get_task(task_id)
        edition_status = state_store.get_edition_status(args.report_id)
        if saved_task:
            print(f"  Task status  : {saved_task['status']}")
            decision = saved_task.get("publish_decision")
            if decision:
                print(f"  Decision     : {decision['decision']} by {decision['decided_by']}")
        print(f"  Edition status: {edition_status}")
    else:
        print("  (dry-run: 실제 DB 상태 확인 생략)")

    print("\n" + "=" * 60)
    print("Publish Flow 완료")
    if not args.dry_run:
        print(f"DB 경로: {Path(__file__).parent.parent / 'data' / 'state.db'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
