#!/usr/bin/env python3
"""
종목별 LLM narrative 자동 생성 스크립트.

create_edition.py 실행 후, publish 전에 실행합니다.
ANTHROPIC_API_KEY가 설정된 경우에만 실제 생성이 수행됩니다.

실행 방법:
    cd weekly_suggest
    python scripts/generate_narratives.py

    # 특정 에디션 지정:
    python scripts/generate_narratives.py --report-id re_20250317_002

    # 이미 생성된 narrative도 재생성:
    python scripts/generate_narratives.py --overwrite

    # 드라이런 (API 호출 없이 흐름만 확인):
    python scripts/generate_narratives.py --dry-run
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.storage.file_store import file_store
from app.core.config import settings


def main():
    parser = argparse.ArgumentParser(description="LLM Narrative 생성")
    parser.add_argument("--report-id", default="re_20250317_002", help="대상 에디션 report_id")
    parser.add_argument("--overwrite", action="store_true", help="기존 narrative 재생성")
    parser.add_argument("--dry-run", action="store_true", help="API 호출 없이 흐름만 확인")
    args = parser.parse_args()

    dry = args.dry_run
    prefix = "[DRY-RUN] " if dry else ""

    print("=" * 62)
    print(f"{prefix}Weekly Suggest: Narrative 자동 생성")
    print(f"  report_id : {args.report_id}")
    print(f"  모델      : {settings.NARRATIVE_MODEL}")
    if not settings.ANTHROPIC_API_KEY:
        print("  [경고] ANTHROPIC_API_KEY 미설정: PLACEHOLDER만 생성됩니다.")
    if dry:
        print("  ※ DRY-RUN 모드: API 호출 없음")
    print("=" * 62)

    # 에디션 로드
    edition = file_store.get_edition_by_id(args.report_id)
    if not edition:
        print(f"\n[오류] 에디션을 찾을 수 없습니다: {args.report_id}")
        print("  data/mock/reports/ 폴더를 확인하세요.")
        sys.exit(1)

    tickers = [s.get("ticker") for s in edition.get("stocks", [])]
    print(f"\n대상 종목: {', '.join(tickers)} ({len(tickers)}개)")

    if dry:
        print("\n[DRY-RUN] 생성될 예정인 종목들:")
        for ticker in tickers:
            report = file_store.get_stock_report(ticker, args.report_id)
            if report:
                existing_status = report.get("analyst_style_summary", {}).get("why_discounted", {}).get("status", "NONE")
                skip = existing_status == "GENERATED" and not args.overwrite
                print(f"  {ticker}: {existing_status} {'(스킵)' if skip else '-> 생성 예정'}")
        print("\n(dry-run 완료: 실제 API 호출 없음)")
        print("=" * 62)
        return

    # 실제 생성
    from app.services.narrative.generator import generate_narratives_for_reports

    reports = []
    for ticker in tickers:
        report = file_store.get_stock_report(ticker, args.report_id)
        if report:
            reports.append(report)
        else:
            print(f"  [경고] {ticker} 리포트 파일 없음 — 스킵")

    print(f"\n[Narrative 생성 시작] {len(reports)}개 종목...")
    results = generate_narratives_for_reports(reports, overwrite_existing=args.overwrite)

    print("\n[생성 결과]")
    for ticker, summary in results.items():
        model = summary.get("model_id", "unknown")
        status = summary.get("why_discounted", {}).get("status", "UNKNOWN")
        print(f"  {ticker:6s} : {status} (model={model})")
        if status == "GENERATED":
            # 첫 블록 미리보기 (앞 50자)
            content = summary["why_discounted"].get("content", "")
            print(f"           why_discounted: {content[:60]}...")

    print()
    print("=" * 62)
    print("Narrative 생성 완료")
    print()
    print("다음 단계: narrative를 StockReport JSON에 반영하려면")
    print("  report_builder.ReportBuilder.build_report(ticker, report_id, generate_narrative=True)")
    print("  또는 Admin 페이지에서 수동 검토 후 llm_narrative_approved = True 설정")
    print("=" * 62)


if __name__ == "__main__":
    main()
