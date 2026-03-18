#!/usr/bin/env python3
"""
격주 발행 D-1 자동 준비 스크립트.

screen -> narrate -> preflight(기본 모드) 3단계를 순서대로 실행하고
결과 리포트를 data/prep_report_YYYYMMDD_HHMMSS.json 에 저장한다.

GitHub Actions 스케줄 또는 로컬에서 직접 실행.
운영자는 실행 결과를 확인 후 review -> prepare -> commit 을 수동 실행한다.

Usage:
    python scripts/biweekly_prep.py
    python scripts/biweekly_prep.py --provider fmp
    python scripts/biweekly_prep.py --dry-run
    python scripts/biweekly_prep.py --skip-screen --context-note "3월 4주차 시황"
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
PREP_SCRIPT  = SCRIPT_DIR / "publish_release.py"
DATA_DIR     = PROJECT_ROOT / "data"


def _run(cmd: list[str], label: str) -> int:
    """subprocess 실행 -- stdout/stderr 터미널에 그대로 출력, exit code 반환."""
    print(f"\n{'=' * 60}")
    print(f"  {label}")
    print(f"{'=' * 60}")
    result = subprocess.run([sys.executable] + cmd)
    return result.returncode


def _save_report(results: dict, ts: str) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    path = DATA_DIR / f"prep_report_{ts}.json"
    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n  준비 리포트: {path.name}")
    except Exception as e:
        print(f"\n  [WARN] 리포트 저장 실패: {e}")


def main() -> None:
    parser = argparse.ArgumentParser(description="격주 발행 D-1 자동 준비 (screen + narrate + preflight)")
    parser.add_argument("--provider",      default=None,  help="데이터 제공자 (mock/fmp/yfinance/hybrid)")
    parser.add_argument("--top-n",         type=int, default=5, help="선정 종목 수 (기본: 5)")
    parser.add_argument("--context-note",  default="",    help="이번 에디션 시황 요약 (preflight 용)")
    parser.add_argument("--dry-run",       action="store_true", help="파일 변경 없이 검증만 실행")
    parser.add_argument("--skip-screen",   action="store_true", help="screen 건너뜀 (기존 staging 사용)")
    parser.add_argument("--skip-narrate",  action="store_true", help="narrate 건너뜀")
    args = parser.parse_args()

    now = datetime.now(timezone.utc)
    ts  = now.strftime("%Y%m%d_%H%M%S")
    results: dict = {
        "started_at": now.isoformat(),
        "provider": args.provider or "default",
        "dry_run": args.dry_run,
        "steps": [],
        "overall": "",
    }

    print(f"\n{'#' * 60}")
    print(f"  Weekly Suggest -- 격주 발행 D-1 자동 준비")
    print(f"  {now.strftime('%Y-%m-%d %H:%M UTC')}")
    print(f"{'#' * 60}")

    # ── Step 1: screen ───────────────────────────────────────
    if not args.skip_screen:
        cmd = [str(PREP_SCRIPT), "screen", "--top-n", str(args.top_n)]
        if args.provider:
            cmd += ["--provider", args.provider]
        if args.dry_run:
            cmd.append("--dry-run")
        code = _run(cmd, "1/3  SCREEN -- 후보 스크리닝 + Staging Draft 생성")
        results["steps"].append({"step": "screen", "exit_code": code,
                                  "status": "OK" if code == 0 else "FAILED"})
        if code != 0:
            print(f"\n[STOP] screen 실패 (exit {code}) -- 이후 단계 중단")
            results["overall"] = "FAILED_AT_SCREEN"
            _save_report(results, ts)
            sys.exit(code)
    else:
        print("\n[SKIP] screen 건너뜀 (--skip-screen)")
        results["steps"].append({"step": "screen", "exit_code": 0, "status": "SKIPPED"})

    # ── Step 2: narrate ──────────────────────────────────────
    if not args.skip_narrate:
        cmd = [str(PREP_SCRIPT), "narrate"]
        if args.dry_run:
            cmd.append("--dry-run")
        code = _run(cmd, "2/3  NARRATE -- Narrative 자동 초안 생성")
        # narrate 실패는 치명적이지 않음 -- preflight DRAFT WARN 으로 계속 진행
        results["steps"].append({"step": "narrate", "exit_code": code,
                                  "status": "OK" if code == 0 else "WARN"})
        if code != 0:
            print(f"\n[WARN] narrate 경고 (exit {code}) -- preflight 에서 DRAFT 체크됨")
    else:
        print("\n[SKIP] narrate 건너뜀 (--skip-narrate)")
        results["steps"].append({"step": "narrate", "exit_code": 0, "status": "SKIPPED"})

    # ── Step 3: preflight (기본 모드 -- DRAFT 는 WARN) ───────
    cmd = [str(PREP_SCRIPT), "preflight"]
    if args.context_note:
        cmd += ["--context-note", args.context_note]
    # D-1 단계: strict 모드 사용 안 함 (DRAFT 상태여도 통과)
    # strict 는 운영자가 review --approve-all 후 직접 확인
    code = _run(cmd, "3/3  PREFLIGHT -- 발행 전 품질 점검 (기본 모드)")
    results["steps"].append({"step": "preflight", "exit_code": code,
                              "status": "OK" if code == 0 else "WARN"})

    # ── 결과 집계 ─────────────────────────────────────────────
    failed  = [s for s in results["steps"] if s["status"] == "FAILED"]
    warned  = [s for s in results["steps"] if s["status"] == "WARN"]
    results["overall"] = "FAILED" if failed else ("READY_WITH_WARNINGS" if warned else "READY")

    _save_report(results, ts)

    print(f"\n{'#' * 60}")
    print(f"  D-1 자동 준비 완료: {results['overall']}")
    print(f"{'#' * 60}")
    print()
    _NEXT = [
        "운영자 다음 단계 (수동):",
        "1. data/staging/ 파일 내용 검토 (종목 데이터 확인)",
        r"2. python scripts\publish_release.py review --show",
        r"3. python scripts\publish_release.py review --approve-all --reviewer <이름>",
        r'4. python scripts\publish_release.py preflight --strict ^',
        r'     --context-note "시황 요약 문구"',
        r"5. python scripts\publish_release.py prepare ^",
        r'     --stocks-dir data\staging --context-note "시황 요약 문구"',
        r"6. python scripts\publish_release.py commit",
        r"7. python scripts\publish_release.py verify",
    ]
    for line in _NEXT:
        print(f"  {line}")
    print()

    # GitHub Actions: WARN 은 0 (경고만), FAILED 는 1
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
