#!/usr/bin/env python3
"""
mock screening 1회 실행 스크립트.

실행 방법:
    cd weekly_suggest
    python scripts/run_screening.py

    # 필터 옵션 오버라이드:
    python scripts/run_screening.py --top-n 3 --min-cap 3.0
"""
import sys
import argparse
from pathlib import Path

# backend를 Python path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

from app.services.screening.pipeline import run_screening
from app.services.provider.mock_provider import mock_provider


def main():
    parser = argparse.ArgumentParser(description="Weekly Suggest 스크리닝 실행")
    parser.add_argument("--top-n", type=int, default=5, help="최종 선정 종목 수 (기본: 5)")
    parser.add_argument("--min-cap", type=float, default=2.0, help="최소 시총 $B (기본: 2.0)")
    parser.add_argument("--verbose", action="store_true", help="상세 출력")
    args = parser.parse_args()

    print("=" * 60)
    print("Weekly Suggest: Mock Screening 실행")
    print("=" * 60)

    result = run_screening(
        provider=mock_provider,
        filters={"min_market_cap_usd_b": args.min_cap},
        top_n=args.top_n,
        use_mock_universe=True,
    )

    print(f"\n[스크리닝 결과]")
    print(f"  Run ID     : {result['run_id']}")
    print(f"  실행 시각  : {result['run_at']}")
    print(f"  전체 후보  : {result['total_candidates']}개")
    print(f"  필터 통과  : {result['passed_filter_count']}개")
    print(f"  필터 제외  : {result['excluded_by_filter_count']}개")
    print(f"  최종 선정  : {result['selected_count']}개")

    print(f"\n[최종 선정 종목]")
    for i, s in enumerate(result["selected"], 1):
        print(f"  {i}. {s['ticker']:6s} | score={s['score']:5.1f} | "
              f"discount={s['sector_discount_pct']:4.1f}% | "
              f"catalyst={s['catalyst_met_count']}/3 | "
              f"risk={s['risk_level_max']}")

    if args.verbose:
        print(f"\n[제외 목록]")
        for e in result["excluded"]:
            score_str = f"score={e['score']:.1f}" if e.get("score") else "필터 제외"
            print(f"  - {e['ticker']:6s} | {score_str:15s} | {e['exclusion_reason']}")

    print("\n적용 필터:", ", ".join(result["filters_applied"]))
    print("=" * 60)


if __name__ == "__main__":
    main()
