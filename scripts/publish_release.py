#!/usr/bin/env python3
"""
Weekly Suggest 발행 자동화 스크립트.

사용법 (Windows CMD):
    cd C:\\Users\\MUSINSA\\Desktop\\Vibe Coding\\weekly_suggest

    REM [선택] 후보 스크리닝 + staging draft 생성
    python scripts\\publish_release.py screen --provider mock

    REM [선택] rule-based narrative 자동 초안 생성
    python scripts\\publish_release.py narrate

    REM [선택] 발행 전 사전 점검
    python scripts\\publish_release.py preflight --context-note "시황 요약"

    REM 1단계: 발행 준비
    python scripts\\publish_release.py prepare --stocks-dir data\\staging ^
      --context-note "시황 요약"

    REM 드라이런 (파일 변경 없이 검증·체크리스트만)
    python scripts\\publish_release.py prepare --stocks-dir data\\staging --dry-run

    REM 2단계: git commit + push
    python scripts\\publish_release.py commit

    REM 3단계: 배포 후 smoke test (Railway 재배포 완료 후)
    python scripts\\publish_release.py verify

전체 자동화 파이프라인 단계:
    Phase 1 (완료): JSON-only 발행 -- prepare / commit / verify
    Phase 2 (완료): screen   -- FMP/yfinance 실데이터 스크리닝 + staging draft 생성
    Phase 3 (완료): narrate  -- rule-based narrative 자동 초안 생성
    Phase 4 (완료): review   -- CLI / Admin UI 운영자 승인 워크플로
    Phase 5 (완료): GitHub Actions 격주 D-1 자동 준비 (scripts/biweekly_prep.py)
    Phase 6 (미정): pdf      -- 발행본 PDF 산출물 생성
"""

import sys
import os
import json
import math
import random
import subprocess
import argparse
from datetime import datetime, timezone, date, timedelta
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError, HTTPError

# ── 경로 설정 (스크립트 위치 기준, CWD 독립) ─────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
REPORTS_DIR  = PROJECT_ROOT / "data" / "mock" / "reports"
LATEST_FILE  = REPORTS_DIR / "edition_latest.json"
STAGING_DIR  = PROJECT_ROOT / "data" / "staging"

DEFAULT_API      = "https://weeklysuggest-production.up.railway.app"
DEFAULT_FRONTEND = "https://weekly-suggest.vercel.app"

DISCLAIMER_BLOCK = {
    "block_id": "db_header_std",
    "position": "HEADER",
    "content": (
        "본 리포트는 투자 권유가 아닙니다. "
        "제시된 분석은 공개된 데이터에 기반한 정보 제공 목적이며, "
        "투자 손익을 보장하지 않습니다. "
        "모든 투자 결정은 투자자 본인의 판단과 책임 하에 이루어져야 합니다."
    ),
    "is_required": True,
}

REQUIRED_STOCK_FIELDS = [
    "ticker", "company_name", "exchange", "sector",
    "current_price", "stock_info", "valuation", "financials",
    "undervaluation_judgment", "catalyst_assessment",
    "publication_meta",
]


# ── 출력 헬퍼 ────────────────────────────────────────────────
def _hr(char="=", width=64):
    print(char * width)

def _section(title):
    print()
    _hr("=")
    print(f"  {title}")
    _hr("=")

def _ok(msg):   print(f"  [OK]   {msg}"); sys.stdout.flush()
def _err(msg):  print(f"  [ERR]  {msg}"); sys.stdout.flush()
def _warn(msg): print(f"  [WARN] {msg}"); sys.stdout.flush()
def _info(msg): print(f"         {msg}"); sys.stdout.flush()


# ── JSON I/O ─────────────────────────────────────────────────
def _read_json(path: Path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _write_json(path: Path, data: dict, dry_run: bool = False) -> None:
    if dry_run:
        _info(f"(dry-run) 쓰기 생략: {path.name}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    _ok(f"저장: {path.relative_to(PROJECT_ROOT)}")


# ── 종목 상세 파일 → 에디션 요약 변환 ────────────────────────
def _extract_stock_summary(detail: dict, report_id: str, edition_num: int) -> dict:
    """종목 상세 JSON에서 edition_latest.json stocks[] 요약 항목을 추출한다."""
    ticker    = detail["ticker"]
    date_part = report_id.split("_")[1]  # YYYYMMDD

    # one_line_thesis: 파일 내 필드 우선, 없으면 discount_narrative에서 자동 추출
    thesis = detail.get("one_line_thesis")
    if not thesis:
        content = (
            detail.get("undervaluation_judgment", {})
                  .get("discount_narrative", {})
                  .get("content", "")
        )
        thesis = (content[:77] + "...") if len(content) > 80 else content

    # valuation_signal
    vd = detail.get("valuation", {}).get("valuation_discount_vs_sector", {})
    uj = detail.get("undervaluation_judgment", {})
    valuation_signal = {
        "sector_discount_pct": vd.get("discount_pct", 0.0),
        "signal_label":        uj.get("combined_signal", "UNKNOWN"),
    }

    # catalyst_badges (A/B/C)
    ca = detail.get("catalyst_assessment", {})
    catalyst_badges = []
    for cid in ("A", "B", "C"):
        cat = ca.get(f"catalyst_{cid.lower()}", {})
        if cat:
            catalyst_badges.append({"catalyst_id": cid, "status": cat.get("status", "UNKNOWN")})

    # risk_level_overall: 최고 severity 기준
    all_risks = detail.get("structural_risks", []) + detail.get("short_term_risks", [])
    _sev_rank = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    max_rank  = max((_sev_rank.get(r.get("severity", "LOW"), 1) for r in all_risks), default=1)
    risk_level = {3: "HIGH", 2: "MEDIUM", 1: "LOW"}[max_rank]

    # data_quality_summary
    flags   = detail.get("data_quality_flags", [])
    _sp     = {"ERROR": 4, "WARNING": 3, "INFO": 2, "NONE": 1}
    highest = max((f.get("severity", "NONE") for f in flags),
                  key=lambda s: _sp.get(s, 0), default="NONE") if flags else "NONE"

    return {
        "report_item_id": f"ri_{date_part}_{edition_num:03d}_{ticker}",
        "ticker":         ticker,
        "company_name":   detail.get("company_name", ""),
        "exchange":       detail.get("exchange", ""),
        "sector":         detail.get("sector", ""),
        "industry":       detail.get("industry", ""),
        "current_price":  detail.get("current_price", {}),
        "market_cap_usd_b": detail.get("stock_info", {}).get("market_cap_usd_b", 0.0),
        "one_line_thesis":  thesis,
        "valuation_signal": valuation_signal,
        "catalyst_badges":  catalyst_badges,
        "risk_level_overall": risk_level,
        "data_quality_summary": {
            "flag_count":       len(flags),
            "highest_severity": highest,
        },
    }


# ── 검증 헬퍼 ────────────────────────────────────────────────
def _validate_stock_detail(data: dict, filename: str) -> list:
    """필수 필드 누락 확인. DRAFT/PUBLISHED 모두 허용 (prepare 에서 PUBLISHED 로 승격)."""
    errors = []
    for field in REQUIRED_STOCK_FIELDS:
        if field not in data:
            errors.append(f"{filename}: 필수 필드 누락 --'{field}'")
    status = data.get("publication_meta", {}).get("status", "")
    if status not in ("PUBLISHED", "DRAFT"):
        errors.append(f"{filename}: publication_meta.status 가 'PUBLISHED' 또는 'DRAFT' 아님 (현재: {status!r})")
    return errors


def _check_placeholder_fields(data: dict, ticker: str) -> None:
    """'[운영자 작성 필요]' 또는 'PLACEHOLDER' 상태 필드를 경고로 출력."""
    placeholders = []
    # 재무 데이터 미완성
    if data.get("financials", {}).get("status") == "UNAVAILABLE":
        placeholders.append("financials (UNAVAILABLE)")
    # analyst_style_summary PLACEHOLDER
    asm = data.get("analyst_style_summary", {})
    for block in ("why_discounted", "why_worth_revisiting", "key_risks_narrative", "investment_context"):
        if asm.get(block, {}).get("status") == "PLACEHOLDER":
            placeholders.append(f"analyst_style_summary.{block}")
    if placeholders:
        _warn(f"{ticker}: 미완성 필드 있음 --{', '.join(placeholders)}")


# ════════════════════════════════════════════════════════════
# rule-based narrative 생성기 (narrate / cmd_narrate 에서 사용)
# ════════════════════════════════════════════════════════════

def _gv(d: dict, *keys, default=None):
    """중첩 dict 에서 키 체인으로 값 추출. 없으면 default."""
    for k in keys:
        if not isinstance(d, dict):
            return default
        d = d.get(k)
        if d is None:
            return default
    return d if d is not None else default


def _sev_rank(s: str) -> int:
    return {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(s, 0)


_DRIVER_LABEL = {
    "금리_고원_장기화":          "금리 고원 장기화",
    "금리_상승":                 "금리 상승",
    "에너지_전환_속도_불확실성":  "에너지 전환 속도 불확실성",
    "관세_인상_자재비_압박":      "관세 인상에 따른 자재비 압박",
    "2025Q4_어닝_미스":          "최근 분기 어닝 미스",
    "수익성_압박":               "수익성 압박",
    "경기_둔화_우려":            "경기 둔화 우려",
    "섹터_로테이션":             "섹터 로테이션",
    "규제_리스크":               "규제 리스크",
    "경쟁_심화":                 "경쟁 심화",
    "환율_리스크":               "환율 리스크",
    "지정학적_리스크":           "지정학적 리스크",
}


def _driver_lbl(d: str) -> str:
    return _DRIVER_LABEL.get(d, d.replace("_", " "))


def _build_why_discounted(data: dict) -> str:
    ticker = data.get("ticker", "이 종목")
    parts  = []

    vds      = _gv(data, "valuation", "valuation_discount_vs_sector", default={})
    metric   = vds.get("metric_used", "")
    sv       = vds.get("stock_value")
    sm       = vds.get("sector_median_value")
    disc_pct = vds.get("discount_pct", 0.0)
    sector_nm = vds.get("sector_comparison_name", "섹터")

    if metric and sv is not None and sm is not None:
        parts.append(
            f"{ticker}의 현재 {metric} {sv}배는 {sector_nm} 중앙값({sm}배) "
            f"대비 약 {disc_pct:.0f}% 할인 상태다."
        )
    elif disc_pct:
        parts.append(f"{ticker}는 섹터 중앙값 대비 약 {disc_pct:.0f}% 할인 상태다.")

    hvp      = _gv(data, "valuation", "historical_valuation_position", default={})
    pct_rank = hvp.get("percentile_rank")
    if pct_rank is not None:
        if pct_rank <= 25:
            parts.append(f"자사 3년 히스토리 하위 {pct_rank}th percentile (역사적 저점 구간)이다.")
        else:
            parts.append(f"자사 3년 히스토리 {pct_rank}th percentile 수준이다.")

    drivers = _gv(data, "undervaluation_judgment", "primary_discount_drivers", default=[])
    if drivers:
        labels = [_driver_lbl(d) for d in drivers[:3]]
        if len(drivers) > 3:
            labels.append(f"외 {len(drivers) - 3}개")
        parts.append(f"주요 할인 원인: {', '.join(labels)}.")

    pc   = data.get("price_context", {})
    dd_v = _gv(pc, "drawdown_from_52w_high_pct", "value") or (
        pc.get("drawdown_from_52w_high_pct")
        if not isinstance(pc.get("drawdown_from_52w_high_pct"), dict)
        else None
    )
    if dd_v is not None and float(dd_v) <= -20:
        parts.append(
            f"52주 고점 대비 {abs(float(dd_v)):.1f}% 하락한 현 주가는 "
            f"기초체력 변화보다 심리적 과매도를 반영하는 것으로 판단된다."
        )

    eps_trend = _gv(data, "financials", "eps_revision_trend")
    if eps_trend == "UPWARD":
        parts.append("EPS 컨센서스는 상향 추세로, 이익 훼손 신호는 관찰되지 않는다.")
    elif eps_trend == "STABLE":
        parts.append("EPS 컨센서스는 안정적으로 유지되고 있다.")

    if not parts:
        parts.append(f"{ticker}는 섹터 및 히스토리 대비 밸류에이션 할인 상태다.")
    return " ".join(parts)


def _build_why_worth_revisiting(data: dict) -> str:
    parts    = []
    ca       = data.get("catalyst_assessment", {})
    met_count = ca.get("met_count", 0)

    met_map = {3: "세 가지 촉매 조건을 모두 충족한다.", 2: "촉매 조건 2/3개를 충족한다.",
               1: "촉매 조건 1/3개를 충족한다."}
    parts.append(met_map.get(met_count, "현재 촉매 조건 충족 수는 제한적이다."))

    for cid in ("catalyst_a", "catalyst_b", "catalyst_c"):
        cat = ca.get(cid, {})
        if cat.get("status") == "MET":
            ev = cat.get("evidence", "")
            if ev:
                parts.append((ev[:97] + "...") if len(ev) > 100 else ev)

    rev_growth = _gv(data, "financials", "revenue_growth_yoy_pct", "value")
    if isinstance(rev_growth, (int, float)) and rev_growth >= 5:
        parts.append(f"매출은 전년 대비 {rev_growth:.1f}% 성장하며 외형 확장을 유지하고 있다.")

    hvp       = _gv(data, "valuation", "historical_valuation_position", default={})
    pct_rank  = hvp.get("percentile_rank")
    tyr_mean  = hvp.get("three_year_mean")
    metric    = _gv(data, "valuation", "valuation_discount_vs_sector", "metric_used", default="")
    sv        = _gv(data, "valuation", "valuation_discount_vs_sector", "stock_value")
    if pct_rank is not None and tyr_mean is not None and sv is not None and metric:
        parts.append(
            f"현재 {metric} {sv}배가 3년 평균({tyr_mean}배)으로 수렴할 경우 "
            f"의미 있는 멀티플 회복 여지가 있다."
        )

    if not parts:
        parts.append("밸류에이션 측면에서 재방문 가치가 있는 상태다.")
    return " ".join(parts)


def _build_key_risks_narrative(data: dict) -> str:
    parts = []

    sev_k = {"HIGH": "고위험", "MEDIUM": "중위험", "LOW": "저위험"}
    sev_k_st = {"HIGH": "단기 고위험", "MEDIUM": "단기 중위험", "LOW": "단기 저위험"}

    for r in sorted(data.get("structural_risks", []),
                    key=lambda x: _sev_rank(x.get("severity", "LOW")), reverse=True)[:2]:
        lbl  = r.get("label", "")
        desc = r.get("description", "")
        sk   = sev_k.get(r.get("severity", ""), "")
        if lbl:
            text = f"[{sk}] {lbl}"
            if desc and len(desc) <= 100:
                text += f": {desc}"
            parts.append(text + ".")

    for r in sorted(data.get("short_term_risks", []),
                    key=lambda x: _sev_rank(x.get("severity", "LOW")), reverse=True)[:1]:
        lbl  = r.get("label", "")
        desc = r.get("description", "")
        sk   = sev_k_st.get(r.get("severity", ""), "단기")
        if lbl:
            text = f"[{sk}] {lbl}"
            if desc and len(desc) <= 100:
                text += f": {desc}"
            parts.append(text + ".")

    nd_ebitda = _gv(data, "financials", "net_debt_to_ebitda", "value")
    if isinstance(nd_ebitda, (int, float)) and nd_ebitda >= 2.0:
        parts.append(f"재무 레버리지(순부채/EBITDA {nd_ebitda}배)가 높아 금리 환경 변화에 민감하다.")

    if not parts:
        all_risks = data.get("structural_risks", []) + data.get("short_term_risks", [])
        parts.append("주요 리스크 항목이 확인되었으나 상세 서술 보완이 필요하다."
                     if all_risks else "현재 식별된 주요 리스크 없음 (운영자 확인 권장).")
    return " ".join(parts)


def _build_investment_context(data: dict) -> str:
    ticker = data.get("ticker", "이 종목")
    parts  = []

    signal    = _gv(data, "undervaluation_judgment", "combined_signal", default="")
    signal_k  = {
        "STRONG_SIGNAL":   "강한 밸류에이션 매력",
        "MODERATE_SIGNAL": "중간 정도의 밸류에이션 매력",
        "WEAK_SIGNAL":     "제한적 밸류에이션 매력",
        "NO_SIGNAL":       "현재 밸류에이션 매력 미충족",
    }.get(signal, "밸류에이션 신호 미분류")

    disc_pct = _gv(data, "valuation", "valuation_discount_vs_sector", "discount_pct", default=0.0)
    metric   = _gv(data, "valuation", "valuation_discount_vs_sector", "metric_used", default="")
    sv       = _gv(data, "valuation", "valuation_discount_vs_sector", "stock_value")

    if metric and sv is not None:
        parts.append(
            f"{ticker}는 {signal_k} 상태다 ({metric} {sv}배, 섹터 대비 {disc_pct:.0f}% 할인)."
        )
    else:
        parts.append(f"{ticker}는 {signal_k} 상태다.")

    met_count = _gv(data, "catalyst_assessment", "met_count", default=0)
    if met_count >= 2:
        parts.append(f"촉매 {met_count}/3개 충족으로 단기~중기 반등 모멘텀의 구조적 조건이 형성돼 있다.")
    elif met_count == 1:
        parts.append("촉매 1/3개 충족으로 모멘텀 조건은 부분적이다.")

    op_margin = _gv(data, "financials", "operating_margin_pct", "value")
    if isinstance(op_margin, (int, float)):
        if op_margin >= 15:
            parts.append(f"영업이익률 {op_margin:.1f}%로 수익 구조는 양호하다.")
        elif op_margin >= 5:
            parts.append(f"영업이익률 {op_margin:.1f}%로 수익성은 안정적이나 개선 여지가 있다.")
        else:
            parts.append(f"영업이익률 {op_margin:.1f}%로 수익성 개선이 핵심 관찰 포인트다.")

    fcf = _gv(data, "financials", "fcf_ttm_b", "value")
    if isinstance(fcf, (int, float)) and fcf > 0:
        parts.append(f"FCF ${fcf:.2f}B는 운영 현금창출 능력을 뒷받침한다.")

    all_risks  = data.get("structural_risks", []) + data.get("short_term_risks", [])
    high_risks = [r for r in all_risks if r.get("severity") == "HIGH"]
    if high_risks:
        parts.append(
            f"고위험 리스크 {len(high_risks)}건이 식별된 만큼, "
            f"매수 전 해당 항목 해소 여부 확인이 선행돼야 한다."
        )
    else:
        parts.append("현재 고위험 리스크는 관찰되지 않으나 중위험 항목 추이는 지속 모니터링이 필요하다.")

    return " ".join(parts)


def _generate_analyst_style_summary(data: dict) -> dict:
    """rule-based 템플릿으로 analyst_style_summary 4개 블록을 생성한다."""
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    return {
        "why_discounted": {
            "content": _build_why_discounted(data),
            "status":  "DRAFT",
            "data_fields_referenced": [
                "valuation.valuation_discount_vs_sector",
                "valuation.historical_valuation_position",
                "undervaluation_judgment.primary_discount_drivers",
            ],
        },
        "why_worth_revisiting": {
            "content": _build_why_worth_revisiting(data),
            "status":  "DRAFT",
            "data_fields_referenced": [
                "catalyst_assessment",
                "financials.eps_fwd_consensus",
                "financials.revenue_growth_yoy_pct",
            ],
        },
        "key_risks_narrative": {
            "content": _build_key_risks_narrative(data),
            "status":  "DRAFT",
            "data_fields_referenced": [
                "structural_risks",
                "short_term_risks",
                "financials.net_debt_to_ebitda",
            ],
        },
        "investment_context": {
            "content": _build_investment_context(data),
            "status":  "DRAFT",
            "data_fields_referenced": [
                "undervaluation_judgment.combined_signal",
                "valuation.valuation_discount_vs_sector",
                "catalyst_assessment",
                "financials.operating_margin_pct",
            ],
        },
        "generated_at":     now_iso,
        "model_id":         "rule-based-v1",
        "reviewer_approved": False,
    }


def _check_narrative_quality(summary: dict, ticker: str) -> None:
    """narrative 블록 내용 길이 경고."""
    for blk in ("why_discounted", "why_worth_revisiting", "key_risks_narrative", "investment_context"):
        content = summary.get(blk, {}).get("content", "")
        if len(content) < 30:
            _warn(f"{ticker}: analyst_style_summary.{blk} 내용이 너무 짧음 ({len(content)}자) --보완 필요")


def _validate_all_json(reports_dir: Path) -> list:
    """reports 디렉토리 전체 JSON 문법 검증."""
    errors = []
    for f in sorted(reports_dir.glob("*.json")):
        try:
            with open(f, "r", encoding="utf-8") as fp:
                json.load(fp)
        except Exception as e:
            errors.append(f"{f.name}: {e}")
    return errors


def _validate_structure(latest: dict, edition_num: int, tickers: list, report_id: str) -> list:
    """에디션 구조 일관성 검증."""
    errors = []

    # edition_latest.json 기본 필드
    if latest.get("edition_number") != edition_num:
        errors.append(
            f"edition_latest: edition_number({latest.get('edition_number')}) ≠ {edition_num}"
        )
    if latest.get("status") != "PUBLISHED":
        errors.append("edition_latest: status가 'PUBLISHED' 아님")
    if not latest.get("market_context_note", "").strip():
        errors.append("edition_latest: market_context_note 비어 있음")
    if not latest.get("stocks"):
        errors.append("edition_latest: stocks 배열 비어 있음")

    # 종목 파일 존재 + report_id 일치
    for ticker in tickers:
        sf = REPORTS_DIR / f"stock_{ticker}_{edition_num:03d}.json"
        if not sf.exists():
            errors.append(f"종목 파일 없음: {sf.name}")
            continue
        try:
            s = _read_json(sf)
            if s.get("report_id") != report_id:
                errors.append(
                    f"{sf.name}: report_id({s.get('report_id')}) ≠ {report_id}"
                )
        except Exception as e:
            errors.append(f"{sf.name}: 읽기 오류 --{e}")

    # 직전 archive 파일 확인 (N>1)
    if edition_num > 1:
        prev_arc = REPORTS_DIR / f"edition_{edition_num - 1:03d}_archive.json"
        if not prev_arc.exists():
            errors.append(f"직전 archive 파일 없음: {prev_arc.name}")
        else:
            try:
                arc = _read_json(prev_arc)
                if arc.get("status") != "ARCHIVED":
                    errors.append(f"{prev_arc.name}: status가 'ARCHIVED' 아님")
                if arc.get("edition_number") != edition_num - 1:
                    errors.append(
                        f"{prev_arc.name}: edition_number({arc.get('edition_number')}) ≠ {edition_num - 1}"
                    )
            except Exception as e:
                errors.append(f"{prev_arc.name}: 읽기 오류 --{e}")

    return errors


# ════════════════════════════════════════════════════════════
# prepare
# ════════════════════════════════════════════════════════════
def cmd_prepare(args):
    dry    = args.dry_run
    prefix = "[DRY-RUN] " if dry else ""

    _section(f"{prefix}발행 준비 (prepare)")

    # 1. 현재 latest 읽기
    print("\n[1/7] 현재 latest 확인...")
    if not LATEST_FILE.exists():
        _err("edition_latest.json 없음. REPORTS_DIR를 확인하세요.")
        _info(f"  경로: {LATEST_FILE}")
        sys.exit(1)

    current    = _read_json(LATEST_FILE)
    cur_num    = current.get("edition_number", 0)
    cur_id     = current.get("report_id", "")
    cur_tickers = [s["ticker"] for s in current.get("stocks", [])]

    _ok(f"현재: VOL.{cur_num}  {cur_id}")
    _info(f"종목: {', '.join(cur_tickers)}")

    # 2. 다음 에디션 번호 / report_id 결정
    print("\n[2/7] 신규 에디션 번호 결정...")
    next_num = cur_num + 1
    pub_date = (args.pub_date or "").strip()
    if pub_date:
        try:
            datetime.strptime(pub_date, "%Y%m%d")
        except ValueError:
            _err(f"--pub-date 형식 오류: '{pub_date}' (YYYYMMDD 필요)")
            sys.exit(1)
    else:
        pub_date = datetime.now(timezone.utc).strftime("%Y%m%d")

    report_id    = f"re_{pub_date}_{next_num:03d}"
    pub_date_fmt = f"{pub_date[:4]}-{pub_date[4:6]}-{pub_date[6:]}"
    published_at = f"{pub_date_fmt}T09:00:00Z"
    data_as_of   = (args.data_as_of or "").strip() or pub_date_fmt

    _ok(f"신규: VOL.{next_num}  {report_id}")
    _info(f"published_at : {published_at}")
    _info(f"data_as_of   : {data_as_of}")

    # 3. staging 디렉토리에서 종목 파일 수집
    print("\n[3/7] 종목 파일 수집...")
    stocks_dir = Path(args.stocks_dir)
    if not stocks_dir.is_absolute():
        stocks_dir = (PROJECT_ROOT / args.stocks_dir).resolve()

    if not stocks_dir.exists():
        _err(f"--stocks-dir 경로 없음: {stocks_dir}")
        _info(f"data/staging/ 에 종목 상세 JSON 파일을 넣어 주세요.")
        sys.exit(1)

    staging_files = sorted(stocks_dir.glob("*.json"))
    if not staging_files:
        _err(f"--stocks-dir 에 .json 파일 없음: {stocks_dir}")
        sys.exit(1)

    new_stocks_detail: list = []
    all_errors: list        = []

    for sf in staging_files:
        try:
            data = _read_json(sf)
        except Exception as e:
            all_errors.append(f"{sf.name}: JSON 파싱 오류 --{e}")
            continue
        errs = _validate_stock_detail(data, sf.name)
        all_errors.extend(errs)
        new_stocks_detail.append(data)

    if all_errors:
        _err(f"종목 파일 검증 오류 {len(all_errors)}건:")
        for e in all_errors:
            _info(e)
        sys.exit(1)

    n_stocks   = len(new_stocks_detail)
    min_stocks = args.min_stocks
    if n_stocks < min_stocks:
        _err(f"종목 수 부족: {n_stocks}개 (최소 {min_stocks}개 필요)")
        sys.exit(1)

    new_tickers = [s["ticker"] for s in new_stocks_detail]
    _ok(f"종목 {n_stocks}개: {', '.join(new_tickers)}")

    # 4. 직전 latest → archive 복사 (status=ARCHIVED)
    print("\n[4/7] 직전 에디션 archive 보존...")
    archive_file = REPORTS_DIR / f"edition_{cur_num:03d}_archive.json"

    if archive_file.exists() and not dry:
        _warn(f"{archive_file.name} 이미 존재 --덮어씁니다.")

    archive_data           = dict(current)
    archive_data["status"] = "ARCHIVED"
    _write_json(archive_file, archive_data, dry)
    _info(f"VOL.{cur_num} → {archive_file.name} (ARCHIVED)")

    # 5. 종목 상세 파일 생성 (report_id / report_item_id / publication_meta 갱신)
    print("\n[5/7] 종목 상세 파일 생성...")
    now_iso              = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    written_stock_files  = []

    for detail in new_stocks_detail:
        ticker   = detail["ticker"]
        dest     = REPORTS_DIR / f"stock_{ticker}_{next_num:03d}.json"
        updated  = dict(detail)
        updated["report_id"]       = report_id
        updated["report_item_id"]  = f"ri_{pub_date}_{next_num:03d}_{ticker}"
        updated["publication_meta"] = {
            "status":         "PUBLISHED",
            "created_at":     now_iso,
            "reviewed_by":    "editor_01",
            "reviewed_at":    now_iso,
            "published_at":   published_at,
            "last_updated_at": now_iso,
        }
        # DRAFT → PUBLISHED 자동 승격 (screen 으로 생성된 draft 파일 처리)
        updated["publication_meta"]["status"] = "PUBLISHED"

        # PLACEHOLDER 필드 경고 (운영자 미완성 항목 식별)
        _check_placeholder_fields(updated, ticker)

        _write_json(dest, updated, dry)
        written_stock_files.append(dest)

    # 6. edition_latest.json 생성
    print("\n[6/7] edition_latest.json 생성...")
    context_note = (args.context_note or "").strip()
    if not context_note:
        _warn("--context-note 없음. market_context_note 가 비어 있습니다.")
        _info("발행 전 edition_latest.json 을 편집기에서 직접 채워주세요.")

    stocks_summary = [
        _extract_stock_summary(d, report_id, next_num)
        for d in new_stocks_detail
    ]

    new_latest = {
        "report_id":           report_id,
        "edition_number":      next_num,
        "issue_type":          args.issue_type,
        "status":              "PUBLISHED",
        "published_at":        published_at,
        "data_as_of":          data_as_of,
        "market_context_note": context_note,
        "screening_run_id":    f"scr_{pub_date}_{next_num:03d}",
        "stocks":              stocks_summary,
        "disclaimer_blocks":   [DISCLAIMER_BLOCK],
        "created_at":          now_iso,
        "last_updated_at":     now_iso,
    }

    _write_json(LATEST_FILE, new_latest, dry)

    # 7. 검증 (JSON 문법 + 구조 일관성)
    print("\n[7/7] 검증...")

    if dry:
        _info("(dry-run) 파일이 생성되지 않아 검증 생략")
        json_errors    = []
        struct_errors  = []
    else:
        json_errors   = _validate_all_json(REPORTS_DIR)
        struct_errors = _validate_structure(new_latest, next_num, new_tickers, report_id)

    has_errors = bool(json_errors or struct_errors)

    for e in json_errors:
        _err(e)
    for e in struct_errors:
        _err(e)

    if not has_errors and not dry:
        _ok("JSON 문법 이상 없음")
        _ok("구조 검증 통과")

    # ── 체크리스트 출력 ──────────────────────────
    print()
    _hr("-")
    print("  발행 준비 체크리스트")
    _hr("-")

    changed_files = (
        [str(LATEST_FILE.relative_to(PROJECT_ROOT)),
         str(archive_file.relative_to(PROJECT_ROOT))]
        + [str(f.relative_to(PROJECT_ROOT)) for f in written_stock_files]
    )

    print(f"\n  신규 에디션  : VOL.{next_num}  ({report_id})")
    print(f"  발행 예정일  : {published_at}")
    print(f"  종목         : {', '.join(new_tickers)}")
    print(f"  archive      : edition_{cur_num:03d}_archive.json (ARCHIVED)")
    print()
    print("  변경 파일 목록:")
    for f in changed_files:
        _info(f)
    print()

    if has_errors:
        print("  [!] 오류 수정 후 prepare 재실행")
    elif dry:
        print("  드라이런 완료. 실제 실행 시 --dry-run 제거")
    else:
        print("  내용 검토 후 다음 단계:")
        _info("python scripts\\publish_release.py commit")
    _hr("-")

    if has_errors:
        sys.exit(1)


# ════════════════════════════════════════════════════════════
# commit
# ════════════════════════════════════════════════════════════
def cmd_commit(args):
    _section("git commit + push (commit)")

    if not LATEST_FILE.exists():
        _err("edition_latest.json 없음. prepare 를 먼저 실행하세요.")
        sys.exit(1)

    latest      = _read_json(LATEST_FILE)
    edition_num = latest.get("edition_number", 0)
    report_id   = latest.get("report_id", "")
    tickers     = [s["ticker"] for s in latest.get("stocks", [])]

    # git add 대상 파일 결정
    files_to_add = [LATEST_FILE]

    if edition_num > 1:
        arc = REPORTS_DIR / f"edition_{edition_num - 1:03d}_archive.json"
        if arc.exists():
            files_to_add.append(arc)
        else:
            _warn(f"{arc.name} 없음 --git add 생략")

    for ticker in tickers:
        sf = REPORTS_DIR / f"stock_{ticker}_{edition_num:03d}.json"
        if sf.exists():
            files_to_add.append(sf)
        else:
            _warn(f"{sf.name} 없음 --git add 생략")

    # ── 차트 JSON 자동 포함 ─────────────────────────────────
    # latest 기준 종목의 chart 파일을 항상 add 목록에 포함한다.
    # 이미 tracked + 변경 없으면 git add는 no-op이므로 안전하다.
    chart_added   = []
    chart_missing = []
    for ticker in tickers:
        cpath = CHART_DIR / f"{ticker}_price_series.json"
        if cpath.exists():
            files_to_add.append(cpath)
            chart_added.append(ticker)
        else:
            chart_missing.append(ticker)
            _warn(f"차트 파일 없음: data/mock/chart/{ticker}_price_series.json "
                  f"→ preflight 에서 ERROR 발생 예정")

    # ── data/mock/chart/ 의 untracked 잔여 파일 감지 ────────
    # screen 이후 생성됐지만 files_to_add 에 빠진 파일을 추가 감지한다.
    _add_set = {str(f) for f in files_to_add}
    try:
        gs = subprocess.run(
            ["git", "status", "--porcelain", "data/mock/chart/"],
            cwd=str(PROJECT_ROOT), capture_output=True, text=True,
        )
        extra_untracked = []
        for line in gs.stdout.splitlines():
            if line.startswith("?? "):
                rel = line[3:].strip()
                abs_path = PROJECT_ROOT / rel
                if str(abs_path) not in _add_set:
                    extra_untracked.append(abs_path)
        if extra_untracked:
            _warn(f"data/mock/chart/ 에 untracked 파일 {len(extra_untracked)}개 추가 감지 — 자동 포함:")
            for ep in extra_untracked:
                files_to_add.append(ep)
                _info(f"  + {ep.relative_to(PROJECT_ROOT)}")
    except Exception:
        pass  # git 미설치 환경 등 예외 무시

    print(f"\n  에디션 : VOL.{edition_num}  ({report_id})")
    print(f"  git add 대상 {len(files_to_add)}개:")
    for f in files_to_add:
        label = str(f.relative_to(PROJECT_ROOT))
        tag   = "  [차트]" if "chart" in label else ""
        _info(f"{label}{tag}")

    if not args.yes and not _confirm("\n  commit + push 하시겠습니까? (y/N): "):
        print("  중단.")
        sys.exit(0)

    # git add
    print()
    rel_paths = [str(f.relative_to(PROJECT_ROOT)).replace("\\", "/") for f in files_to_add]
    result = subprocess.run(
        ["git", "add"] + rel_paths,
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _err(f"git add 실패:\n{result.stderr}")
        sys.exit(1)
    _ok("git add 완료")

    # git commit
    commit_msg = (args.message or "").strip()
    if not commit_msg:
        commit_msg = f"publish: VOL.{edition_num} {report_id} 정기 발행"

    result = subprocess.run(
        ["git", "commit", "-m", commit_msg],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _err(f"git commit 실패:\n{result.stderr.strip()}")
        _info("스테이징된 변경사항이 없을 수 있습니다. git status 로 확인하세요.")
        sys.exit(1)
    _ok(f"git commit: {commit_msg}")
    print(f"  {result.stdout.strip()}")

    # git push
    if args.no_push:
        _warn("--no-push: push 생략")
        _info("수동 push: git push")
        return

    print()
    result = subprocess.run(
        ["git", "push"],
        cwd=str(PROJECT_ROOT),
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        _err(f"git push 실패:\n{result.stderr.strip()}")
        sys.exit(1)
    _ok("git push 완료")
    print()
    _ok("Railway 자동 재배포 시작 (완료까지 약 3~5분)")
    _info("완료 후: python scripts\\publish_release.py verify")


def _confirm(prompt: str) -> bool:
    try:
        return input(prompt).strip().lower() == "y"
    except (KeyboardInterrupt, EOFError):
        return False


# ════════════════════════════════════════════════════════════
# screen --헬퍼
# ════════════════════════════════════════════════════════════

def _load_dotenv() -> None:
    """backend/.env 또는 루트 .env 가 있으면 os.environ 에 로드 (python-dotenv 없이)."""
    for candidate in (PROJECT_ROOT / "backend" / ".env", PROJECT_ROOT / ".env"):
        if not candidate.exists():
            continue
        try:
            with open(candidate, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, _, val = line.partition("=")
                    key = key.strip()
                    val = val.strip().strip('"').strip("'")
                    if key and key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass
        break  # 첫 번째 파일만


def _inject_backend_path() -> None:
    """scripts/ 위치에서 backend/ 패키지를 import 가능하도록 sys.path 에 추가.
    backend/venv 의 site-packages 도 함께 등록한다."""
    backend = str(PROJECT_ROOT / "backend")
    if backend not in sys.path:
        sys.path.insert(0, backend)

    # venv site-packages 탐색 (Windows: venv/Lib/site-packages, Unix: venv/lib/python*/site-packages)
    venv_root = PROJECT_ROOT / "backend" / "venv"
    if venv_root.exists():
        # Windows
        win_sp = venv_root / "Lib" / "site-packages"
        if win_sp.exists() and str(win_sp) not in sys.path:
            sys.path.insert(1, str(win_sp))
            return
        # Unix/macOS
        for lib in sorted((venv_root / "lib").glob("python*")):
            sp = lib / "site-packages"
            if sp.exists() and str(sp) not in sys.path:
                sys.path.insert(1, str(sp))
                return


def _find_best_stock_file(ticker: str) -> Optional[Path]:
    """reports/ 에서 ticker 에 해당하는 가장 최신 stock 상세 파일 반환."""
    candidates = sorted(REPORTS_DIR.glob(f"stock_{ticker.upper()}_*.json"))
    return candidates[-1] if candidates else None


def _make_draft_from_file(stock_file: Path) -> dict:
    """기존 stock 파일을 읽어 DRAFT 상태로 변환. report_id/report_item_id 제거."""
    draft = _read_json(stock_file)
    now   = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    draft["publication_meta"] = {
        "status":          "DRAFT",
        "created_at":      now,
        "reviewed_by":     None,
        "reviewed_at":     None,
        "published_at":    None,
        "last_updated_at": now,
    }
    # 이전 에디션 식별자 제거 (prepare 가 새로 부여)
    draft.pop("report_id",      None)
    draft.pop("report_item_id", None)
    return draft


def _make_draft_from_candidate(candidate: dict) -> dict:
    """
    reports/ 에 stock 파일이 없을 때 스크리닝 candidate 데이터로
    최소 구조의 draft 를 생성한다.
    운영자가 재무 데이터 등을 직접 채워야 하는 골격 파일이다.
    """
    now     = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    ticker  = candidate["ticker"]
    sector  = candidate.get("sector", "")
    disc    = candidate.get("sector_discount_pct", 0.0)
    met     = candidate.get("catalyst_met_count", 0)

    if disc >= 25 and met >= 2:
        signal = "STRONG_SIGNAL"
    elif disc >= 15 and met >= 1:
        signal = "MODERATE_SIGNAL"
    elif disc >= 10:
        signal = "WEAK_SIGNAL"
    else:
        signal = "NO_SIGNAL"

    _na = {"value": None, "status": "UNAVAILABLE"}

    return {
        "ticker":       ticker,
        "company_name": candidate.get("company_name", ticker),
        "exchange":     candidate.get("exchange", "NYSE"),
        "sector":       sector,
        "industry":     candidate.get("industry", ""),
        "stock_info": {
            "short_description": "[운영자 작성 필요]",
            "headquarters":      None,
            "market_cap_usd_b":  candidate.get("market_cap_usd_b", 0.0),
            "employee_count":    {"value": None, "status": "UNAVAILABLE"},
            "fiscal_year_end":   "12-31",
        },
        "current_price": {
            "value":    candidate.get("current_price", 0.0),
            "currency": "USD",
            "as_of":    now,
        },
        "price_context": {
            "week_52_high":              {"value": candidate.get("week_52_high"),    "status": "CONFIRMED"},
            "week_52_low":               {"value": candidate.get("week_52_low"),     "status": "CONFIRMED"},
            "week_52_position_pct":      {"value": candidate.get("week_52_position_pct"), "status": "CONFIRMED"},
            "drawdown_from_52w_high_pct": _na,
            "price_1m_change_pct":       _na,
            "price_3m_change_pct":       _na,
            "price_6m_change_pct":       _na,
            "price_ytd_change_pct":      _na,
            "as_of": datetime.now(timezone.utc).date().isoformat(),
        },
        "interest_price_range": {
            "status": "UNAVAILABLE",
            "lower_bound": None, "upper_bound": None,
            "basis_metric": "Fwd P/E",
            "conditional_statement": "[운영자 작성 필요]",
            "disclaimer": "이 가격 범위는 목표주가가 아닙니다.",
        },
        "valuation": {
            "primary_metric": "Fwd P/E",
            "metrics": {
                "fwd_per":      _na, "trailing_per": _na,
                "ev_ebitda":    _na, "pb":           _na,
                "ps":           _na, "p_fcf":        _na,
            },
            "valuation_discount_vs_sector": {
                "status":                  "ESTIMATED",
                "metric_used":             "Fwd P/E",
                "stock_value":             None,
                "sector_median_value":     None,
                "discount_pct":            disc,
                "sector_comparison_name":  f"{sector} Sector Peers",
                "comparison_universe_count": 20,
            },
            "historical_valuation_position": {
                "status": "UNAVAILABLE",
                "metric_used": "Fwd P/E",
                "current_value": None, "three_year_mean": None,
                "three_year_min": None, "three_year_max": None,
                "percentile_rank": None,
            },
        },
        "financials": {
            "status":                  "UNAVAILABLE",
            "fiscal_year":             "[운영자 작성 필요]",
            "revenue_ttm_b":           _na, "revenue_growth_yoy_pct": _na,
            "operating_income_ttm_b":  _na, "operating_margin_pct":   _na,
            "net_income_ttm_b":        _na, "eps_ttm":                _na,
            "eps_fwd_consensus":       _na, "eps_revision_trend":     "NEUTRAL",
            "fcf_ttm_b":               _na, "net_debt_b":             _na,
            "net_debt_to_ebitda":      _na, "interest_coverage_ratio": _na,
            "roe_pct":                 _na,
        },
        "undervaluation_judgment": {
            "is_discounted_vs_sector":  disc > 0,
            "is_discounted_vs_history": False,
            "combined_signal":          signal,
            "primary_discount_drivers": ["[운영자 작성 필요]"],
            "discount_narrative": {
                "content": f"스크리닝 기준 섹터 대비 {disc:.1f}% 할인. 운영자 검토 후 서술 보완 필요.",
                "status":  "PLACEHOLDER",
                "data_fields_referenced": [],
            },
        },
        "catalyst_assessment": {
            "catalyst_a": {
                "catalyst_id": "A",
                "definition_summary": "90일 이내 실적 발표 + 컨센서스 상향/유지",
                "status": "MET" if met >= 1 else "NOT_MET",
                "evidence": "[운영자 확인 필요]",
                "data_status": "ESTIMATED",
            },
            "catalyst_b": {
                "catalyst_id": "B",
                "definition_summary": "애널리스트 목표가 괴리율 20% 이상 + 커버리지 3명 이상",
                "status": "MET" if met >= 2 else "NOT_MET",
                "evidence": "[운영자 확인 필요]",
                "data_status": "ESTIMATED",
            },
            "catalyst_c": {
                "catalyst_id": "C",
                "definition_summary": "52주 고점 대비 30% 이상 하락 + EPS 하향 폭 50% 미만",
                "status": "MET" if met >= 3 else "NOT_MET",
                "evidence": "[운영자 확인 필요]",
                "data_status": "ESTIMATED",
            },
            "met_count":       met,
            "composite_label": f"복합 촉매 {met}/3 충족 (추정)",
        },
        "bull_case_points": [
            {"point_id": 1, "summary": "[운영자 작성 필요]", "detail": "",
             "confidence": "MEDIUM", "is_data_backed": False}
        ],
        "bear_case_points": [
            {"point_id": 1, "summary": "[운영자 작성 필요]", "detail": "",
             "confidence": "MEDIUM", "is_data_backed": False}
        ],
        "structural_risks": [
            {"risk_id": f"sr_{ticker.lower()}_001", "category": "UNKNOWN",
             "label": "[운영자 작성 필요]", "description": "",
             "severity": candidate.get("risk_level_max", "MEDIUM"),
             "data_status": "ESTIMATED"}
        ],
        "short_term_risks": [],
        "analyst_style_summary": {
            "why_discounted":      {"content": "[운영자 또는 narrate 서브커맨드 실행 필요]", "status": "PLACEHOLDER", "data_fields_referenced": []},
            "why_worth_revisiting": {"content": "[운영자 또는 narrate 서브커맨드 실행 필요]", "status": "PLACEHOLDER", "data_fields_referenced": []},
            "key_risks_narrative":  {"content": "[운영자 또는 narrate 서브커맨드 실행 필요]", "status": "PLACEHOLDER", "data_fields_referenced": []},
            "investment_context":   {"content": "[운영자 또는 narrate 서브커맨드 실행 필요]", "status": "PLACEHOLDER", "data_fields_referenced": []},
            "generated_at":        now,
            "model_id":            "placeholder",
            "reviewer_approved":   False,
        },
        "data_quality_flags": [
            {
                "flag_id":   f"dqf_{ticker.lower()}_draft",
                "field_path": "financials",
                "flag_type":  "DRAFT_INCOMPLETE",
                "message":    "스크리닝 draft 파일입니다. 재무 데이터 및 서술 보완 필요.",
                "severity":   "WARNING",
            }
        ],
        "data_sources": [
            {"source_id": "ds_screen_001", "provider_name": "screening_auto",
             "data_category": "universe_screening", "as_of": now}
        ],
        "disclaimer_blocks": [DISCLAIMER_BLOCK],
        "publication_meta": {
            "status":          "DRAFT",
            "created_at":      now,
            "reviewed_by":     None,
            "reviewed_at":     None,
            "published_at":    None,
            "last_updated_at": now,
        },
    }


# ════════════════════════════════════════════════════════════
# screen
# ════════════════════════════════════════════════════════════

def cmd_screen(args):
    _section("후보 종목 스크리닝 (screen)")

    # ── 환경 준비 ───────────────────────────────────────────
    _load_dotenv()
    _inject_backend_path()

    provider_mode = (args.provider or os.getenv("DATA_PROVIDER_MODE", "mock")).lower().strip()

    # ── [1/4] Provider 확인 ──────────────────────────────────
    print("\n[1/4] Provider 모드 확인...")

    if provider_mode == "mock":
        try:
            from app.services.provider.mock_provider import mock_provider as provider
            _ok("Provider: mock  (실데이터 연결 전 개발 모드)")
        except ImportError as e:
            _err(f"backend import 실패: {e}")
            _info(f"  경로 확인: {PROJECT_ROOT / 'backend'}")
            sys.exit(1)

    elif provider_mode == "fmp":
        api_key = os.getenv("FMP_API_KEY", "")
        if not api_key:
            _warn("FMP_API_KEY 없음 -- mock 모드로 fallback")
            _info("  실데이터 사용: backend/.env 에서 FMP_API_KEY=<key> 설정 후 재실행")
            from app.services.provider.mock_provider import mock_provider as provider
            provider_mode = "mock"
        else:
            try:
                from app.services.provider.fmp_provider import FMPDataProvider
                provider = FMPDataProvider(api_key=api_key)
                _ok(f"Provider: FMP (실데이터 모드)")
            except ImportError as e:
                _err(f"FMP provider import 실패: {e}")
                sys.exit(1)

    elif provider_mode in ("yfinance", "hybrid"):
        try:
            import yfinance  # noqa: F401
        except ImportError:
            _warn("yfinance 패키지 없음 -- mock 모드로 fallback")
            _info("  설치: pip install yfinance>=0.2.40")
            from app.services.provider.mock_provider import mock_provider as provider
            provider_mode = "mock"
        else:
            try:
                from app.services.provider.factory import get_provider
                provider = get_provider()
                _ok(f"Provider: {provider_mode}")
            except ImportError as e:
                _err(f"provider import 실패: {e}")
                sys.exit(1)

    else:
        _warn(f"알 수 없는 provider: '{provider_mode}' → mock 으로 fallback")
        from app.services.provider.mock_provider import mock_provider as provider
        provider_mode = "mock"

    use_mock_universe = (provider_mode == "mock")

    # ── [2/4] 스크리닝 실행 ──────────────────────────────────
    print(f"\n[2/4] 스크리닝 실행 (top-{args.top_n})...")
    try:
        from app.services.screening.pipeline import run_screening
        result = run_screening(provider, top_n=args.top_n,
                               use_mock_universe=use_mock_universe)
    except Exception as e:
        _err(f"스크리닝 실패: {e}")
        sys.exit(1)

    selected  = result["selected"]
    total     = result["total_candidates"]
    passed    = result["passed_filter_count"]
    excluded  = result["excluded"]

    print(f"      후보 {total}개 → 필터 통과 {passed}개 → 선정 {len(selected)}개\n")

    # ── 실데이터 모드: 부족한 필드 안내 ─────────────────────
    if not use_mock_universe and selected:
        missing_fields = []
        for s in selected:
            if s.get("sector_discount_pct") is None or s.get("sector_discount_pct") == 0.0:
                missing_fields.append(f"{s['ticker']}: sector_discount_pct (valuation 데이터 없음)")
            if s.get("catalyst_met_count") is None:
                missing_fields.append(f"{s['ticker']}: catalyst_met_count (컨센서스/어닝 없음)")
        if missing_fields:
            _warn("일부 스코어링 필드가 기본값(0)으로 계산됨 -- 정확도 제한:")
            for msg in missing_fields[:5]:
                _info(f"  {msg}")
            if len(missing_fields) > 5:
                _info(f"  ... 외 {len(missing_fields)-5}개")
    print(f"  {'#':>2}  {'Ticker':<6}  {'Score':>5}  {'Disc%':>7}  {'Catalyst':>8}  {'Risk':<8}  종목명")
    print("  " + "-" * 68)
    for i, s in enumerate(selected, 1):
        print(
            f"  {i:>2}  {s['ticker']:<6}  {s['score']:>5.1f}  "
            f"{s.get('sector_discount_pct', 0):>6.1f}%  "
            f"     {s.get('catalyst_met_count', 0)}/3  "
            f"{s.get('risk_level_max', '?'):<8}  {s['company_name']}"
        )

    if args.show_excluded and excluded:
        print(f"\n  [제외 {len(excluded)}개]")
        for e in excluded[:8]:
            reason = e.get("exclusion_reason", "?")
            print(f"       {e['ticker']:<6}  {reason}")

    # ── [3/4] Draft 파일 생성 ────────────────────────────────
    print(f"\n[3/4] Draft 파일 생성 → data/staging/")
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    draft_files  = []
    draft_sources = []

    for s in selected:
        ticker = s["ticker"]
        dest   = STAGING_DIR / f"stock_{ticker}_draft.json"

        # 전략 1: reports/ 에 기존 stock 파일 있으면 복사 + DRAFT 변환
        existing = _find_best_stock_file(ticker)
        if existing:
            draft  = _make_draft_from_file(existing)
            source = f"기존 파일 기반: {existing.name}"
        else:
            # 전략 2: ReportBuilder 로 구조 생성 (real provider 연동 시 유효)
            draft = None
            if provider_mode != "mock":
                try:
                    from app.services.report_builder import ReportBuilder
                    builder = ReportBuilder(provider)
                    draft   = builder.build_report(ticker, "re_DRAFT_000")
                    if draft:
                        # DRAFT 상태 + 식별자 제거
                        draft["publication_meta"]["status"] = "DRAFT"
                        draft.pop("report_id",      None)
                        draft.pop("report_item_id", None)
                        source = "ReportBuilder 생성 (real provider)"
                except Exception as e:
                    _warn(f"{ticker}: ReportBuilder 실패 ({e}) → 최소 draft 생성")
                    draft = None

            # 전략 3: candidate 데이터로 최소 골격 draft 생성
            if draft is None:
                draft  = _make_draft_from_candidate(s)
                source = "스크리닝 데이터 기반 골격 (운영자 보완 필요)"

        if not args.dry_run:
            _write_json(dest, draft)
        else:
            _info(f"(dry-run) 생성 생략: {dest.name}")

        draft_files.append(dest)
        draft_sources.append((ticker, source))
        _info(f"{ticker:<6}  {source}")

    # ── [4/5] 차트 파일 자동 생성 ────────────────────────────
    print(f"\n[4/5] 차트 파일 자동 생성...")
    CHART_DIR.mkdir(parents=True, exist_ok=True)
    chart_results: list = []

    for s in selected:
        ticker     = s["ticker"]
        chart_path = CHART_DIR / f"{ticker}_price_series.json"

        # 이미 존재하면 건너뜀 (덮어쓰지 않음)
        if chart_path.exists():
            chart_results.append((ticker, "SKIP", "기존 파일 유지"))
            _info(f"{ticker:<6}  [SKIP] 차트 파일 이미 존재")
            continue

        # 가격 데이터 추출
        current_price = s.get("current_price")
        week52_high   = s.get("week_52_high")
        week52_low    = s.get("week_52_low")

        if not current_price:
            chart_results.append((ticker, "WARN", "current_price 없음 → 수동 생성 필요"))
            _warn(f"{ticker}: current_price 없음 → 차트 자동 생성 건너뜀 (수동 생성 필요)")
            continue

        # 기본값 fallback (실데이터 미연동 시)
        if not week52_high:
            week52_high = round(current_price * 1.35, 2)
            _warn(f"{ticker}: week_52_high 없음 → current_price × 1.35 사용 ({week52_high})")
        if not week52_low:
            week52_low  = round(current_price * 0.70, 2)
            _warn(f"{ticker}: week_52_low 없음  → current_price × 0.70 사용 ({week52_low})")

        if args.dry_run:
            chart_results.append((ticker, "DRY", "생성 예정 (dry-run)"))
            _info(f"{ticker:<6}  [DRY-RUN] 차트 생성 예정 (현재가={current_price})")
            continue

        try:
            chart_data = _gen_chart_for_ticker(ticker, current_price, week52_high, week52_low)
            _write_json(chart_path, chart_data)
            series_len = len(chart_data["data"])
            chart_results.append((ticker, "NEW", f"series={series_len}"))
            _ok(f"{ticker:<6}  [NEW] 차트 생성 완료  series={series_len}")
        except Exception as e:
            chart_results.append((ticker, "ERR", str(e)))
            _err(f"{ticker}: 차트 생성 실패 → {e}")

    # ── [5/5] 완료 요약 ──────────────────────────────────────
    print()
    _hr("-")
    print("  스크리닝 완료 요약")
    _hr("-")

    print(f"\n  Provider   : {provider_mode}")
    print(f"  선정 종목  : {', '.join(s['ticker'] for s in selected)}")
    print()
    print("  Draft 파일 목록:")
    for f in draft_files:
        tag = "(예정)" if args.dry_run else ""
        _info(f"data/staging/{f.name}  {tag}")

    draft_ok   = [t for t, src in draft_sources if "골격" not in src]
    draft_skel = [t for t, src in draft_sources if "골격" in src]

    if draft_skel:
        print()
        _warn(f"골격 draft 종목 {len(draft_skel)}개 --재무 데이터 및 서술 직접 보완 필요:")
        for t in draft_skel:
            _info(f"  {t}: financials, analyst_style_summary, bull/bear_case_points 등")

    # 차트 생성 결과 요약
    print()
    print("  차트 파일:")
    for ticker, status, msg in chart_results:
        tag = f"[{status}]"
        _info(f"{ticker:<6}  {tag:<8}  {msg}")

    chart_warn = [t for t, s, _ in chart_results if s in ("WARN", "ERR")]
    if chart_warn:
        print()
        _warn(f"차트 자동 생성 실패 종목 {len(chart_warn)}개 — 수동 생성 필요: {', '.join(chart_warn)}")
        _info(f"  참고: scripts/_gen_chart_data.py 또는 직접 파일 작성 후 preflight 재실행")

    # 신규 생성 차트 파일 git add 안내
    new_chart_tickers = [t for t, s, _ in chart_results if s == "NEW"]
    if new_chart_tickers:
        print()
        _warn(f"신규 차트 파일 {len(new_chart_tickers)}개 생성됨 — commit 단계에서 자동 포함됩니다.")
        _info("  생성된 파일 목록:")
        for t in new_chart_tickers:
            _info(f"    data/mock/chart/{t}_price_series.json")
        _info("")
        _info("  지금 바로 git add 하려면:")
        paths = " ".join(f"data/mock/chart/{t}_price_series.json" for t in new_chart_tickers)
        _info(f"    git add {paths}")

    print()
    print("  다음 단계:")
    _info("1. data/staging/ 의 draft 파일 검토 및 보완")
    if draft_skel:
        _info("   특히 '[운영자 작성 필요]' 표시 필드를 채워야 합니다")
    _info("2. market_context_note 문구 준비")
    _info("3. 발행 준비 실행:")
    _info("   python scripts\\publish_release.py prepare --stocks-dir data\\staging \\")
    _info('     --context-note "이번 에디션 시황 요약"')
    _hr("-")

    if draft_skel:
        print(f"\n  [주의] 골격 draft {len(draft_skel)}개는 운영자 보완 전 prepare 실행 불가.")
        print(f"          (prepare 의 구조 검증에서 publication_meta.status 확인됨)")


# ════════════════════════════════════════════════════════════
# narrate --rule-based analyst_style_summary 생성
# ════════════════════════════════════════════════════════════
def cmd_narrate(args):
    _section("rule-based narrative 생성 (narrate)")

    stocks_dir = Path(args.stocks_dir)
    if not stocks_dir.exists():
        _err(f"디렉토리 없음: {stocks_dir}")
        sys.exit(1)

    stock_files = sorted(
        f for f in stocks_dir.glob("*.json")
        if not f.name.startswith("edition_")
    )
    if not stock_files:
        _warn(f"종목 JSON 파일 없음: {stocks_dir}")
        _info("screen 실행 후 draft 파일을 생성하거나 직접 종목 파일을 준비하세요.")
        sys.exit(1)

    print(f"\n  대상 디렉토리: {stocks_dir.relative_to(PROJECT_ROOT)}")
    print(f"  종목 파일 수 : {len(stock_files)}개")
    print()

    generated = []
    skipped   = []

    for fpath in stock_files:
        try:
            data = _read_json(fpath)
        except Exception as e:
            _err(f"{fpath.name}: 읽기 오류 --{e}")
            continue

        ticker = data.get("ticker", fpath.stem)

        # 기존 summary 확인
        existing = data.get("analyst_style_summary", {})
        if existing and not args.overwrite:
            blocks_status = [
                existing.get(b, {}).get("status", "")
                for b in ("why_discounted", "why_worth_revisiting",
                          "key_risks_narrative", "investment_context")
            ]
            already_done = all(s and s != "PLACEHOLDER" for s in blocks_status)
            if already_done and existing.get("model_id") not in ("rule-based-v1", ""):
                _info(f"{ticker:<8} 스킵 -- 기존 narrative 있음 (model_id={existing.get('model_id', '?')})")
                _info(f"         덮어쓰려면 --overwrite 옵션 사용")
                skipped.append(ticker)
                continue

        summary       = _generate_analyst_style_summary(data)
        data["analyst_style_summary"] = summary

        if not args.dry_run:
            _write_json(fpath, data)
            _ok(f"{ticker:<8} analyst_style_summary 생성 완료 (DRAFT)")
        else:
            _info(f"{ticker:<8} (dry-run) 생성 생략")

        _check_narrative_quality(summary, ticker)
        generated.append(ticker)

    # ── 완료 요약 ────────────────────────────────────────────
    print()
    _hr("-")
    print("  narrate 완료 요약")
    _hr("-")
    print(f"\n  생성: {len(generated)}개  |  스킵: {len(skipped)}개")
    if generated:
        print(f"  종목: {', '.join(generated)}")
    print()
    print("  모든 블록은 status='DRAFT' 로 생성됩니다.")
    print("  운영자 검토 절차:")
    print()
    _info("1. data/staging/ 각 종목 파일의 analyst_style_summary 내용 검토·수정")
    _info("2. 수정 완료된 블록: status 'DRAFT' → 'APPROVED' 로 변경")
    _info("3. publication_meta.reviewed_by 에 검토자 ID 입력 (선택)")
    _info("4. 사전 점검:")
    _info("   python scripts\\publish_release.py preflight --stocks-dir data\\staging")
    _info("5. 발행 준비:")
    _info(f"   python scripts\\publish_release.py prepare --stocks-dir {args.stocks_dir}")
    _info('     --context-note "이번 에디션 시황 요약"')
    _hr("-")


# ════════════════════════════════════════════════════════════
# ── 차트 파일 생성·검증 헬퍼 ─────────────────────────────────
CHART_DIR = PROJECT_ROOT / "data" / "mock" / "chart"


def _chart_make_dates(start: date, end: date) -> list:
    """주간(7일) 거래일 날짜 목록 생성."""
    dates, d = [], start
    while d <= end:
        dates.append(d.strftime("%Y-%m-%d"))
        d += timedelta(days=7)
    return dates


def _chart_lerp_path(anchors: list, dates: list) -> list:
    """앵커 포인트 사이를 선형 보간해 종가(close) 시계열 반환."""
    a_dates  = [date.fromisoformat(a[0]) for a in anchors]
    a_prices = [a[1] for a in anchors]
    closes   = []
    for d_str in dates:
        d_obj = date.fromisoformat(d_str)
        if d_obj <= a_dates[0]:
            closes.append(a_prices[0]); continue
        if d_obj >= a_dates[-1]:
            closes.append(a_prices[-1]); continue
        for i in range(len(a_dates) - 1):
            if a_dates[i] <= d_obj <= a_dates[i + 1]:
                span    = (a_dates[i + 1] - a_dates[i]).days
                elapsed = (d_obj - a_dates[i]).days
                t       = elapsed / span if span > 0 else 0
                closes.append(round(a_prices[i] + t * (a_prices[i + 1] - a_prices[i]), 2))
                break
    return closes


def _chart_gen_ohlcv(dates: list, closes: list, seed: int = 42) -> list:
    """종가 시계열로부터 OHLCV 바 생성. seed로 재현성 보장."""
    rng    = random.Random(seed)
    result = []
    prev   = closes[0]
    for d_str, close in zip(dates, closes):
        vol   = close * 0.02
        high  = round(close + abs(rng.gauss(0, vol * 1.2)), 2)
        low   = round(close - abs(rng.gauss(0, vol * 1.2)), 2)
        open_ = round(prev   + rng.gauss(0, vol * 0.5),    2)
        high  = max(high, open_, close)
        low   = min(low,  open_, close)
        result.append({
            "date": d_str, "open": open_, "high": high,
            "low": low, "close": close,
            "volume": int(rng.uniform(500_000, 3_000_000)),
        })
        prev = close
    return result


def _gen_chart_for_ticker(
    ticker: str,
    current_price: float,
    week52_high: float,
    week52_low: float,
) -> dict:
    """신규 종목 차트 JSON을 스크리닝 데이터 기반으로 자동 생성.

    가격 경로:
      T-52w  → 52주 고점 인근 (97%)
      T-39w  → 52주 고점
      T-13w  → 52주 저점
      T-now  → 현재가 (반등 상태)

    interest_range_band:  52주 저점 +2% ~ +15% 를 관심 구간으로 설정.
    스키마: lower_bound / upper_bound (표준, 2026-03-18 이후 규칙).
    """
    today = datetime.now(timezone.utc).date()
    start = today - timedelta(weeks=52)
    end   = today - timedelta(days=7)

    dates   = _chart_make_dates(start, end)
    anchors = [
        (start.strftime("%Y-%m-%d"),                          round(week52_high * 0.97, 2)),
        ((start + timedelta(weeks=13)).strftime("%Y-%m-%d"),  round(week52_high,        2)),
        ((start + timedelta(weeks=39)).strftime("%Y-%m-%d"),  round(week52_low,         2)),
        (end.strftime("%Y-%m-%d"),                            round(current_price,      2)),
    ]
    closes = _chart_lerp_path(anchors, dates)
    ohlcv  = _chart_gen_ohlcv(dates, closes, seed=abs(hash(ticker)) % (2 ** 31))

    # reference_lines: 52주 고점 / 저점
    reference_lines = [
        {"label": "WEEK_52_HIGH", "value": week52_high, "color_hint": "#ef4444"},
        {"label": "WEEK_52_LOW",  "value": week52_low,  "color_hint": "#22c55e"},
    ]

    # event_markers: 과거 4분기 실적 (90일 간격)
    event_markers = []
    for q in range(4):
        ed = today - timedelta(days=45 + q * 91)
        closest = min(dates, key=lambda x: abs(date.fromisoformat(x) - ed))
        idx = dates.index(closest)
        event_markers.append({
            "date":       closest,
            "event_type": "EARNINGS_RELEASE",
            "label":      f"Q{4 - q} Earnings",
            "price":      closes[idx],
        })

    # interest_range_band: 52주 저점 기준 +2% ~ +15%
    irb_low  = round(week52_low * 1.02, 2)
    irb_high = round(min(week52_low * 1.15, current_price * 1.05), 2)

    return {
        "ticker":    ticker.upper(),
        "interval":  "1wk",
        "data":      ohlcv,
        "reference_lines":   reference_lines,
        "event_markers":     event_markers,
        "interest_range_band": {
            "lower_bound": irb_low,
            "upper_bound": irb_high,
            "label":       "관심 가격 구간",
            "color_hint":  "rgba(59,130,246,0.12)",
        },
    }


def _check_chart_files(tickers: list) -> list:
    """staging 기준 종목 목록의 차트 JSON 파일 존재 + 구조 검증.

    반환: [(ticker, severity, message), ...]
      severity: "ERROR" | "WARN"

    검사 항목:
      [E1] 차트 파일 자체가 없음
      [E2] 차트 파일 읽기 오류 (JSON 파싱 실패 등)
      [E3] price_series / data 배열이 비어 있음 → API 빈 배열 반환
      [E4] interest_range_band 키 불일치
           - lower_bound/upper_bound 없고 low/high만 있으면 _transform_chart()에서
             irb=None 처리 → 차트 관심구간 미표시 (2026-03-18 인시던트 재발 방지)
           - lower_bound/upper_bound/low/high 모두 없으면 스키마 오류
      [W1] price_series 포인트 수 부족 (< 10)
      [W2] reference_lines 없음 (52주 고점/저점 미표시)
      [W3] event_markers 없음 (분기 실적 마커 미표시)
    """
    issues = []

    for ticker in tickers:
        chart_path = CHART_DIR / f"{ticker}_price_series.json"

        # [E1] 파일 존재 여부
        if not chart_path.exists():
            issues.append((
                ticker, "ERROR",
                f"차트 파일 없음: data/mock/chart/{ticker}_price_series.json "
                f"→ 상세 페이지 404 발생 가능",
            ))
            continue

        # [E2] 파일 읽기
        try:
            data = _read_json(chart_path)
        except Exception as e:
            issues.append((ticker, "ERROR", f"차트 파일 읽기 오류: {e}"))
            continue

        # [E3] price_series 비어있는지 (mock JSON은 "data" 키, 표준은 "price_series")
        raw_series = data.get("data", data.get("price_series", []))
        if not raw_series:
            issues.append((
                ticker, "ERROR",
                "price_series 비어 있음 → 차트 API 빈 배열 반환 → 차트 미표시",
            ))
        elif len(raw_series) < 10:
            issues.append((
                ticker, "WARN",
                f"price_series 포인트 수 적음 ({len(raw_series)}개, 권장 ≥ 10)",
            ))

        # [E4] interest_range_band 스키마 검증
        irb = data.get("interest_range_band")
        if irb is not None:
            has_new = "lower_bound" in irb and "upper_bound" in irb
            has_old = "low" in irb or "high" in irb
            if not has_new and has_old:
                issues.append((
                    ticker, "ERROR",
                    "interest_range_band: lower_bound/upper_bound 없음, low/high만 있음 "
                    "→ _transform_chart() irb=None 처리, 관심구간 미표시 "
                    "(lower_bound/upper_bound 키로 수정 필요)",
                ))
            elif not has_new and not has_old:
                issues.append((
                    ticker, "ERROR",
                    "interest_range_band 키 구조 오류: "
                    "lower_bound/upper_bound/low/high 모두 없음",
                ))

        # [W2] reference_lines 없음
        if not data.get("reference_lines"):
            issues.append((
                ticker, "WARN",
                "reference_lines 없음 (52주 고점/저점 참조선 미표시)",
            ))

        # [W3] event_markers 없음
        if not data.get("event_markers"):
            issues.append((
                ticker, "WARN",
                "event_markers 없음 (분기 실적 이벤트 마커 미표시)",
            ))

    return issues


# ════════════════════════════════════════════════════════════
# preflight --prepare 실행 전 사전 점검
# ════════════════════════════════════════════════════════════
def cmd_preflight(args):
    _section("발행 전 사전 점검 (preflight)")

    stocks_dir   = Path(args.stocks_dir)
    context_note = (args.context_note or "").strip()

    issues   = []   # (ticker_or_scope, severity, message)
    warnings = []

    staged_tickers: list = []   # [2/5]에서 수집 → [5/5]에서 사용

    # ── [1] market_context_note ──────────────────────────────
    print("\n[1/5] market_context_note 확인...")
    if not context_note:
        issues.append(("edition", "ERROR", "--context-note 가 비어 있음 --prepare 실행 시 필수"))
        _err("market_context_note 없음")
    else:
        _ok(f"market_context_note: {context_note[:60]}{'...' if len(context_note) > 60 else ''}")

    # ── [2] 종목 파일 존재 + 최소 구조 ───────────────────────
    print("\n[2/5] 종목 파일 구조 확인...")
    if not stocks_dir.exists():
        issues.append(("staging", "ERROR", f"디렉토리 없음: {stocks_dir}"))
        _err(f"디렉토리 없음: {stocks_dir}")
    else:
        stock_files = sorted(
            f for f in stocks_dir.glob("*.json")
            if not f.name.startswith("edition_")
        )
        if not stock_files:
            issues.append(("staging", "ERROR", "종목 파일 없음"))
            _err("종목 파일 없음")
        else:
            _ok(f"{len(stock_files)}개 파일 발견")
            for fpath in stock_files:
                try:
                    data   = _read_json(fpath)
                    ticker = data.get("ticker", fpath.stem)
                    staged_tickers.append(ticker.upper())  # [5/5] 차트 검사용
                    errs   = _validate_stock_detail(data, fpath.name)
                    for e in errs:
                        issues.append((ticker, "ERROR", e))
                        _err(f"{ticker}: {e}")
                    if not errs:
                        _ok(f"{ticker:<8} 필수 필드 OK")
                except Exception as e:
                    issues.append((fpath.name, "ERROR", f"읽기 오류: {e}"))
                    _err(f"{fpath.name}: {e}")

    # ── [3] narrative 완성도 ─────────────────────────────────
    print("\n[3/5] analyst_style_summary 완성도 확인...")
    NARRATIVE_BLOCKS = ("why_discounted", "why_worth_revisiting",
                        "key_risks_narrative", "investment_context")
    if stocks_dir.exists():
        stock_files = sorted(
            f for f in stocks_dir.glob("*.json")
            if not f.name.startswith("edition_")
        )
        for fpath in stock_files:
            try:
                data   = _read_json(fpath)
                ticker = data.get("ticker", fpath.stem)
                asm    = data.get("analyst_style_summary", {})

                if not asm:
                    msg = "analyst_style_summary 없음 --narrate 먼저 실행하세요"
                    if getattr(args, "strict", False):
                        issues.append((ticker, "ERROR", msg))
                        _err(f"{ticker}: {msg}")
                    else:
                        warnings.append((ticker, "WARN", msg))
                        _warn(f"{ticker}: narrative 없음 --narrate 실행 권장")
                    continue

                for blk in NARRATIVE_BLOCKS:
                    blk_data = asm.get(blk, {})
                    status   = blk_data.get("status", "")
                    content  = blk_data.get("content", "")

                    if status == "PLACEHOLDER" or not content:
                        issues.append((ticker, "ERROR",
                                       f"analyst_style_summary.{blk} 미완성 (status={status!r})"))
                        _err(f"{ticker}: {blk} 미완성")
                    elif status == "DRAFT":
                        msg = f"analyst_style_summary.{blk} DRAFT -- review --approve-all 로 승인 필요"
                        if getattr(args, "strict", False):
                            issues.append((ticker, "ERROR", msg))
                            _err(f"{ticker}: {blk} DRAFT (strict 모드: APPROVED 필요)")
                        else:
                            warnings.append((ticker, "WARN", msg))
                            _warn(f"{ticker}: {blk} DRAFT --검토 권장")
                    elif len(content) < 30:
                        warnings.append((ticker, "WARN",
                                         f"analyst_style_summary.{blk} 내용 너무 짧음 ({len(content)}자)"))
                        _warn(f"{ticker}: {blk} 내용 너무 짧음 ({len(content)}자)")
                    else:
                        _ok(f"{ticker:<8} {blk} OK (status={status})")

            except Exception:
                pass

    # ── [4] placeholder / UNAVAILABLE 잔존 ───────────────────
    print("\n[4/5] placeholder·미완성 필드 확인...")
    _PLACEHOLDER_MARKERS = ("[운영자 작성 필요]", "PLACEHOLDER", "[TODO]", "[TBD]")
    if stocks_dir.exists():
        stock_files = sorted(
            f for f in stocks_dir.glob("*.json")
            if not f.name.startswith("edition_")
        )
        for fpath in stock_files:
            try:
                raw    = fpath.read_text(encoding="utf-8")
                data   = json.loads(raw)
                ticker = data.get("ticker", fpath.stem)
                found  = []

                for marker in _PLACEHOLDER_MARKERS:
                    if marker in raw:
                        found.append(marker)

                if _gv(data, "financials", "status") == "UNAVAILABLE":
                    found.append("financials.status=UNAVAILABLE")

                if found:
                    warnings.append((ticker, "WARN",
                                     f"미완성 마커 잔존: {', '.join(found)}"))
                    _warn(f"{ticker}: {', '.join(found)}")
                else:
                    _ok(f"{ticker:<8} 미완성 마커 없음")
            except Exception:
                pass

    # ── [5] 차트 파일 존재 + 스키마 검증 ────────────────────
    print("\n[5/5] 차트 파일 확인...")
    if not staged_tickers:
        _warn("종목 없음 — 차트 검사 건너뜀")
    else:
        _info(f"대상 종목: {', '.join(staged_tickers)}")
        chart_issues = _check_chart_files(staged_tickers)
        if not chart_issues:
            for ticker in staged_tickers:
                _ok(f"{ticker:<8} 차트 파일 OK")
        else:
            # 정상 종목 OK 출력
            error_tickers = {t for t, sev, _ in chart_issues if sev == "ERROR"}
            warn_tickers  = {t for t, sev, _ in chart_issues if sev == "WARN" and t not in error_tickers}
            for ticker in staged_tickers:
                if ticker not in error_tickers and ticker not in warn_tickers:
                    _ok(f"{ticker:<8} 차트 파일 OK")
            for ticker, sev, msg in chart_issues:
                if sev == "ERROR":
                    issues.append((ticker, "ERROR", msg))
                    _err(f"{ticker}: {msg}")
                else:
                    warnings.append((ticker, "WARN", msg))
                    _warn(f"{ticker}: {msg}")

    # ── 결과 집계 ────────────────────────────────────────────
    print()
    _hr("-")
    print("  preflight 결과")
    _hr("-")

    error_count = sum(1 for _, sev, _ in issues if sev == "ERROR")
    warn_count  = len(warnings)

    strict = getattr(args, "strict", False)
    mode_label = " [strict 모드]" if strict else ""

    if error_count == 0 and warn_count == 0:
        _ok(f"모든 점검 통과{mode_label} --prepare 실행 가능")
    elif error_count == 0:
        _warn(f"경고 {warn_count}건 (오류 없음){mode_label} --prepare 실행 가능하지만 검토 권장")
        for ticker, _, msg in warnings:
            _info(f"  [{ticker}] {msg}")
    else:
        _err(f"오류 {error_count}건 발생 --prepare 실행 전 아래 항목 수정 필요:")
        for ticker, sev, msg in issues:
            marker = "[ERR]" if sev == "ERROR" else "[WARN]"
            _info(f"  {marker} [{ticker}] {msg}")
        if warnings:
            print()
            _warn(f"추가 경고 {warn_count}건:")
            for ticker, _, msg in warnings:
                _info(f"  [WARN] [{ticker}] {msg}")
        print()
        _hr("-")
        sys.exit(1)

    print()
    if error_count == 0:
        _info("다음 단계:")
        _info(f"  python scripts\\publish_release.py prepare --stocks-dir {args.stocks_dir}")
        _info('    --context-note "이번 에디션 시황 요약"')
    _hr("-")


# ════════════════════════════════════════════════════════════
# review — narrative 블록 검토/승인 (batch CLI)
# ════════════════════════════════════════════════════════════

_NARRATIVE_BLOCKS = ("why_discounted", "why_worth_revisiting",
                     "key_risks_narrative", "investment_context")
_BLOCK_LABELS = {
    "why_discounted":      "왜 할인됐나",
    "why_worth_revisiting": "왜 재방문 가치가 있나",
    "key_risks_narrative": "핵심 리스크",
    "investment_context":  "투자 맥락",
}


def cmd_review(args):
    _section("narrative 검토 (review)")

    stocks_dir = Path(args.stocks_dir)
    if not stocks_dir.exists():
        _err(f"디렉토리 없음: {stocks_dir}")
        sys.exit(1)

    stock_files = sorted(
        f for f in stocks_dir.glob("*.json")
        if not f.name.startswith("edition_")
    )
    if not stock_files:
        _warn("종목 파일 없음")
        sys.exit(1)

    # ── --show: 상태만 출력 ───────────────────────────────────
    if args.show:
        print()
        _hr("-")
        print("  narrative 검토 상태")
        _hr("-")
        all_done = True
        for fpath in stock_files:
            try:
                data   = _read_json(fpath)
                ticker = data.get("ticker", fpath.stem)
                asm    = data.get("analyst_style_summary", {})
                pm     = data.get("publication_meta", {})
                rev_by = pm.get("reviewed_by") or "없음"
                rev_at = pm.get("reviewed_at") or ""
                approved_flag = asm.get("reviewer_approved", False)
                model  = asm.get("model_id", "?")

                print(f"\n  {ticker}")
                print(f"    reviewer_approved : {approved_flag}")
                print(f"    reviewed_by       : {rev_by}")
                if rev_at:
                    print(f"    reviewed_at       : {rev_at}")
                print(f"    model_id          : {model}")

                ticker_done = True
                for blk in _NARRATIVE_BLOCKS:
                    status  = asm.get(blk, {}).get("status", "없음")
                    content = asm.get(blk, {}).get("content", "")
                    icon    = "[v]" if status == "APPROVED" else "[?]" if status == "DRAFT" else "[x]"
                    length  = f"  ({len(content)}자)" if content else ""
                    print(f"    {icon} {_BLOCK_LABELS[blk]:<18} {status}{length}")
                    if status != "APPROVED":
                        ticker_done = False
                if not ticker_done:
                    all_done = False
            except Exception as e:
                _err(f"{fpath.name}: {e}")

        print()
        _hr("-")
        if all_done:
            _ok("모든 종목 검토 완료 -- preflight --strict 통과 가능")
        else:
            _warn("미승인 블록 있음 -- review --approve-all 실행 권장")
        _hr("-")
        return

    # ── batch approval (--approve-all / --ticker) ────────────
    if not args.approve_all and not args.ticker:
        _err("--show, --approve-all, 또는 --ticker TICK1 중 하나를 지정하세요")
        _info("예시:")
        _info("  python scripts\\publish_release.py review --show")
        _info("  python scripts\\publish_release.py review --approve-all")
        _info("  python scripts\\publish_release.py review --ticker MFGI")
        sys.exit(1)

    reviewer = (args.reviewer or "editor_01").strip()
    now_iso  = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    target_tickers = (
        None if args.approve_all
        else {t.strip().upper() for t in args.ticker.split(",")}
    )

    print(f"\n  검토자    : {reviewer}")
    print(f"  대상      : {'전체' if target_tickers is None else ', '.join(sorted(target_tickers))}")
    print(f"  dry-run   : {args.dry_run}")
    print()

    approved_tickers = []
    skipped_tickers  = []

    for fpath in stock_files:
        try:
            data   = _read_json(fpath)
            ticker = data.get("ticker", fpath.stem)

            if target_tickers is not None and ticker not in target_tickers:
                continue

            asm = data.get("analyst_style_summary", {})
            if not asm:
                _warn(f"{ticker}: analyst_style_summary 없음 --narrate 먼저 실행하세요")
                skipped_tickers.append(ticker)
                continue

            changed    = False
            short_blks = []

            for blk in _NARRATIVE_BLOCKS:
                blk_data = asm.get(blk, {})
                status   = blk_data.get("status", "")
                content  = blk_data.get("content", "")

                if status == "APPROVED":
                    continue  # 이미 승인됨

                if len(content) < 30:
                    short_blks.append(blk)
                    _warn(f"{ticker}.{blk}: 내용 너무 짧음 ({len(content)}자) --수정 후 승인하세요")
                    continue

                asm[blk]["status"] = "APPROVED"
                changed = True

            if short_blks:
                _warn(f"{ticker}: {len(short_blks)}개 블록은 내용 부족으로 승인 보류됨")

            if not changed:
                _info(f"{ticker:<8} 변경 없음 (모두 이미 승인됨 또는 내용 부족)")
                skipped_tickers.append(ticker)
                continue

            # reviewer_approved: 모든 블록이 APPROVED인 경우 true
            all_approved = all(
                asm.get(b, {}).get("status") == "APPROVED"
                for b in _NARRATIVE_BLOCKS
            )
            asm["reviewer_approved"] = all_approved

            pm = data.get("publication_meta", {})
            pm["reviewed_by"]       = reviewer
            pm["reviewed_at"]       = now_iso
            pm["last_updated_at"]   = now_iso
            data["publication_meta"]       = pm
            data["analyst_style_summary"]  = asm

            if not args.dry_run:
                _write_json(fpath, data)
                status_str = "전체 APPROVED" if all_approved else "일부 APPROVED"
                _ok(f"{ticker:<8} 승인 완료 [{status_str}]  reviewer={reviewer}")
            else:
                _info(f"{ticker:<8} (dry-run) 승인 생략")

            approved_tickers.append(ticker)

        except Exception as e:
            _err(f"{fpath.name}: {e}")

    # ── 완료 요약 ────────────────────────────────────────────
    print()
    _hr("-")
    print("  review 완료 요약")
    _hr("-")
    print(f"\n  승인 완료: {len(approved_tickers)}개  |  스킵: {len(skipped_tickers)}개")
    if approved_tickers:
        print(f"  승인 종목: {', '.join(approved_tickers)}")
    print()
    if approved_tickers:
        _info("다음 단계 (검토 완료 강제 점검):")
        _info(f"  python scripts\\publish_release.py preflight --strict")
        _info(f'    --stocks-dir {args.stocks_dir}')
        _info(f'    --context-note "이번 에디션 시황 요약"')
    _hr("-")


# ════════════════════════════════════════════════════════════
# verify
# ════════════════════════════════════════════════════════════
def cmd_verify(args):
    _section("배포 후 smoke test (verify)")

    api      = args.api.rstrip("/")
    frontend = args.frontend.rstrip("/")

    if not LATEST_FILE.exists():
        _err("edition_latest.json 없음")
        sys.exit(1)

    latest           = _read_json(LATEST_FILE)
    expected_num     = latest.get("edition_number", 0)
    expected_id      = latest.get("report_id", "")
    expected_stocks  = latest.get("stocks", [])
    expected_tickers = [s["ticker"] for s in expected_stocks]

    print(f"\n  API URL      : {api}")
    if not args.skip_frontend:
        print(f"  Frontend URL : {frontend}")
    print(f"  기대 에디션  : VOL.{expected_num}  ({expected_id})")
    print(f"  기대 종목    : {', '.join(expected_tickers)}")
    print()

    results = []

    # ① /health
    data, err = _http_get(f"{api}/health")
    if err:
        results.append((False, "/health", err))
    else:
        build     = data.get("build", "unknown")
        admin_set = data.get("diag_admin_key_set")
        results.append((True, "/health", f"build={build}  admin_key_set={admin_set}"))

    # ② /api/v1/reports/latest --edition_number + tickers 일치
    data, err = _http_get(f"{api}/api/v1/reports/latest")
    if err:
        results.append((False, "/reports/latest", err))
    else:
        d              = data.get("data", {})
        actual_num     = d.get("edition_number")
        actual_tickers = [s["ticker"] for s in d.get("stocks", [])]
        ok  = (actual_num == expected_num and
               set(actual_tickers) == set(expected_tickers))
        results.append((ok, "/reports/latest",
                         f"VOL.{actual_num}  {actual_tickers}"))

    # ③ /api/v1/archive --각 VOL 1건, 중복 없음
    data, err = _http_get(f"{api}/api/v1/archive")
    if err:
        results.append((False, "/archive", err))
    else:
        arr      = data.get("data", [])
        nums     = [e.get("edition_number") for e in arr]
        has_dup  = len(nums) != len(set(nums))
        ok       = not has_dup and expected_num in nums
        results.append((ok, "/archive",
                         f"에디션 {len(arr)}개: {sorted(nums)}  "
                         f"중복={'있음' if has_dup else '없음'}"))

    # ④ /api/v1/archive/{N-1} --ARCHIVED 확인
    if expected_num > 1:
        prev = expected_num - 1
        data, err = _http_get(f"{api}/api/v1/archive/{prev}")
        if err:
            results.append((False, f"/archive/{prev}", err))
        else:
            d  = data.get("data", {})
            ok = (d.get("edition_number") == prev and d.get("status") == "ARCHIVED")
            results.append((ok, f"/archive/{prev}",
                             f"VOL.{d.get('edition_number')}  {d.get('status')}"))

    # ⑤ 종목 상세 /{report_id}/stocks/{ticker[0]}
    if expected_tickers:
        t0        = expected_tickers[0]
        data, err = _http_get(f"{api}/api/v1/reports/{expected_id}/stocks/{t0}")
        if err:
            results.append((False, f"/stocks/{t0}", err))
        else:
            d  = data.get("data", {})
            ok = (d.get("ticker") == t0 and d.get("report_id") == expected_id)
            results.append((ok, f"/stocks/{t0}",
                             f"ticker={d.get('ticker')}  report_id={d.get('report_id')}"))

    # ⑥ /api/v1/admin/review-tasks --반드시 403
    code, err = _http_status(f"{api}/api/v1/admin/review-tasks")
    if err:
        results.append((False, "/admin/review-tasks", f"요청 오류: {err}"))
    else:
        ok = code == 403
        results.append((ok, "/admin/review-tasks", f"HTTP {code}  (기대: 403)"))

    # ⑦ 차트 API — latest 기준 5개 종목 전체 검증
    #   체크 항목:
    #   [E] HTTP 200 이 아닌 경우 (500 등)                    → ok=False
    #   [E] price_series 배열이 비어 있음                     → ok=False
    #   [W] interest_range_band = null (irb 없음)             → 기록만, ok=True
    #   [W] reference_lines / event_markers 없음              → 기록만, ok=True
    if expected_tickers:
        print()
        _info(f"차트 API 검증 ({len(expected_tickers)}개 종목)...")
        for ticker in expected_tickers:
            label     = f"/chart/{ticker}"
            chart_url = f"{api}/api/v1/chart/{ticker}?period_days=365"
            data, err = _http_get(chart_url)

            if err:
                # HTTP 500 등 오류 응답 또는 연결 실패
                results.append((False, label, err))
                continue

            d          = data.get("data", {})
            series     = d.get("price_series", [])
            series_len = len(series)
            has_series = series_len > 0

            # 부가 정보 (WARN 수준 — ok 판정에 영향 없음)
            notes = []
            if d.get("interest_range_band") is None:
                notes.append("irb=없음")
            if not d.get("reference_lines"):
                notes.append("ref_lines=없음")
            if not d.get("event_markers"):
                notes.append("events=없음")
            note_str = f"  [{', '.join(notes)}]" if notes else ""

            if has_series:
                msg = f"HTTP 200  series={series_len}{note_str}"
            else:
                msg = f"HTTP 200  series=0 (비어 있음 — 차트 미표시){note_str}"

            results.append((has_series, label, msg))

    # ⑧ Vercel 프론트엔드 페이지 HTTP 검증
    #   체크 항목:
    #   [E] HTTP 200 이 아닌 경우 → ok=False  (404 포함)
    #   백엔드 API와 분리된 별도 섹션으로 출력한다
    frontend_results = []

    if not args.skip_frontend:
        print()
        _info(f"Vercel 프론트엔드 검증 ({frontend})...")

        # ⑧-1  메인 페이지 /
        code, err = _http_status(f"{frontend}/", timeout=20)
        if err:
            frontend_results.append((False, "Vercel /", f"연결 오류: {err}"))
        else:
            frontend_results.append((code == 200, "Vercel /", f"HTTP {code}"))

        # ⑧-2  아카이브 목록 /archive
        code, err = _http_status(f"{frontend}/archive", timeout=20)
        if err:
            frontend_results.append((False, "Vercel /archive", f"연결 오류: {err}"))
        else:
            frontend_results.append((code == 200, "Vercel /archive", f"HTTP {code}"))

        # ⑧-3  종목 상세 5개 /report/{report_item_id}?report_id={report_id}
        for stock in expected_stocks:
            item_id = stock.get("report_item_id", "")
            ticker  = stock.get("ticker", "")
            label   = f"Vercel /report/{item_id}"
            page_url = f"{frontend}/report/{item_id}?report_id={expected_id}"
            code, err = _http_status(page_url, timeout=20)
            if err:
                frontend_results.append((False, label, f"연결 오류: {err}"))
            else:
                msg = f"HTTP {code}"
                if code == 404:
                    msg += "  ← 상세 페이지 없음 (SSR 오류 또는 캐시 미갱신)"
                elif code != 200:
                    msg += "  ← 예상치 않은 응답"
                frontend_results.append((code == 200, label, msg))

    # ── 결과 출력 — 백엔드 Railway ────────────────────────────
    print()
    _hr("-")
    print("  [백엔드 Railway]")
    _hr("-")
    for ok, label, msg in results:
        marker = "OK  " if ok else "FAIL"
        sym    = "  [v]" if ok else "  [x]"
        print(f"{sym} [{marker}]  {label:<50}  {msg}")

    be_pass = sum(1 for ok, _, _ in results if ok)
    be_fail = len(results) - be_pass

    # ── 결과 출력 — 프론트엔드 Vercel ────────────────────────
    if frontend_results:
        print()
        _hr("-")
        print("  [프론트엔드 Vercel]")
        _hr("-")
        for ok, label, msg in frontend_results:
            marker = "OK  " if ok else "FAIL"
            sym    = "  [v]" if ok else "  [x]"
            print(f"{sym} [{marker}]  {label:<50}  {msg}")
        if any(not ok for ok, _, _ in frontend_results):
            print()
            print("  ※ 상세 페이지 404는 Vercel SSR 캐시 지연일 수 있습니다.")
            print("    Railway 배포 후 3~5분 대기 → 재실행 권장.")

    fe_pass = sum(1 for ok, _, _ in frontend_results if ok)
    fe_fail = len(frontend_results) - fe_pass

    total_pass = be_pass + fe_pass
    total_fail = be_fail + fe_fail
    total      = len(results) + len(frontend_results)

    print()
    _hr("=")
    if total_fail == 0:
        print(f"  결과: {total_pass}/{total} 통과  -- 백엔드 + 프론트엔드 발행 검증 완료")
    else:
        if be_fail > 0 and fe_fail > 0:
            label_fail = f"백엔드 {be_fail}건 / 프론트엔드 {fe_fail}건"
        elif be_fail > 0:
            label_fail = f"백엔드 {be_fail}건"
        else:
            label_fail = f"프론트엔드 {fe_fail}건"
        print(f"  결과: {total_pass}/{total} 통과  실패 {label_fail} -- 위 항목 확인")
    _hr("=")

    if total_fail > 0:
        sys.exit(1)


# ── HTTP 헬퍼 ─────────────────────────────────────────────────
def _http_get(url: str, timeout: int = 10):
    """(data_dict, error_str) 반환. 오류 시 data=None."""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except HTTPError as e:
        return None, f"HTTP {e.code}"
    except URLError as e:
        return None, f"연결 오류: {e.reason}"
    except Exception as e:
        return None, str(e)


def _http_status(url: str, timeout: int = 10):
    """(status_code, error_str) 반환."""
    try:
        req = Request(url, headers={"Accept": "application/json"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.status, None
    except HTTPError as e:
        return e.code, None
    except URLError as e:
        return None, str(e.reason)
    except Exception as e:
        return None, str(e)


# ════════════════════════════════════════════════════════════
# 인수 파싱 + 진입점
# ════════════════════════════════════════════════════════════
def main():
    parser = argparse.ArgumentParser(
        prog="publish_release.py",
        description="Weekly Suggest 발행 자동화",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "사용 예시:\n"
            "  python scripts\\publish_release.py prepare --stocks-dir data\\staging\n"
            "  python scripts\\publish_release.py prepare --stocks-dir data\\staging --dry-run\n"
            "  python scripts\\publish_release.py commit\n"
            "  python scripts\\publish_release.py verify\n"
        ),
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    # ── prepare ──
    p = sub.add_parser("prepare", help="발행 준비: archive 보존, 파일 생성, 검증")
    p.add_argument(
        "--stocks-dir", default=str(STAGING_DIR),
        help=f"종목 상세 JSON 파일 디렉토리 (기본: data/staging)",
    )
    p.add_argument("--context-note",  default="", help="market_context_note (시황 요약)")
    p.add_argument("--pub-date",      default="", help="발행일 YYYYMMDD (기본: 오늘)")
    p.add_argument("--data-as-of",    default="", help="데이터 기준일 YYYY-MM-DD (기본: pub-date)")
    p.add_argument(
        "--issue-type", default="REGULAR_BIWEEKLY",
        choices=["REGULAR_BIWEEKLY", "EARNINGS_TRIGGERED", "SPECIAL_EVENT"],
        help="발행 유형 (기본: REGULAR_BIWEEKLY)",
    )
    p.add_argument("--min-stocks", type=int, default=5, help="최소 종목 수 (기본: 5)")
    p.add_argument("--dry-run",    action="store_true", help="파일 변경 없이 검증·출력만")

    # ── commit ──
    p = sub.add_parser("commit", help="git add/commit/push")
    p.add_argument("--message",  default="",  help="커밋 메시지 (기본: 자동 생성)")
    p.add_argument("--no-push",  action="store_true", help="push 생략 (commit만)")
    p.add_argument("-y", "--yes", action="store_true", help="확인 프롬프트 생략")

    # ── screen ──
    p = sub.add_parser("screen", help="후보 종목 스크리닝 + staging draft 생성")
    p.add_argument(
        "--provider",
        default="",
        choices=["", "mock", "fmp", "yfinance", "hybrid"],
        help="데이터 provider (기본: .env DATA_PROVIDER_MODE 또는 mock)",
    )
    p.add_argument(
        "--top-n", type=int, default=5,
        help="선정 종목 수 (기본: 5)",
    )
    p.add_argument(
        "--show-excluded", action="store_true",
        help="필터 제외 종목 목록 출력",
    )
    p.add_argument(
        "--dry-run", action="store_true",
        help="draft 파일 생성 없이 결과만 출력",
    )

    # ── narrate ──
    p = sub.add_parser("narrate", help="staging draft 에 rule-based analyst_style_summary 자동 생성")
    p.add_argument(
        "--stocks-dir", default=str(STAGING_DIR),
        help=f"종목 draft JSON 디렉토리 (기본: data/staging)",
    )
    p.add_argument(
        "--overwrite", action="store_true",
        help="기존 analyst_style_summary 덮어쓰기 (기본: 기존 있으면 스킵)",
    )
    p.add_argument("--dry-run", action="store_true", help="파일 변경 없이 출력만")

    # ── review ──
    p = sub.add_parser("review", help="staging narrative 블록 검토 상태 확인 및 batch 승인")
    p.add_argument(
        "--stocks-dir", default=str(STAGING_DIR),
        help=f"종목 draft JSON 디렉토리 (기본: data/staging)",
    )
    p.add_argument("--show",        action="store_true", help="검토 상태만 출력 (파일 변경 없음)")
    p.add_argument("--approve-all", action="store_true", help="모든 종목의 DRAFT 블록을 APPROVED로 일괄 승인")
    p.add_argument("--ticker",      default="",          help="특정 종목만 승인 (쉼표 구분 가능, 예: MFGI,RVNC)")
    p.add_argument("--reviewer",    default="editor_01", help="검토자 ID (기본: editor_01)")
    p.add_argument("--dry-run",     action="store_true", help="파일 변경 없이 출력만")

    # ── preflight ──
    p = sub.add_parser("preflight", help="prepare 실행 전 사전 점검 (narrative·placeholder·context-note)")
    p.add_argument(
        "--stocks-dir", default=str(STAGING_DIR),
        help=f"종목 draft JSON 디렉토리 (기본: data/staging)",
    )
    p.add_argument("--context-note", default="", help="market_context_note 문구 (비어 있으면 경고)")
    p.add_argument(
        "--strict", action="store_true",
        help="DRAFT narrative 블록을 경고 대신 오류로 처리 (review --approve-all 완료 후 사용)",
    )

    # ── verify ──
    p = sub.add_parser("verify", help="배포 후 smoke test")
    p.add_argument(
        "--api", default=DEFAULT_API,
        help=f"API 베이스 URL (기본: {DEFAULT_API})",
    )
    p.add_argument(
        "--frontend", default=DEFAULT_FRONTEND,
        help=f"Vercel 프론트엔드 URL (기본: {DEFAULT_FRONTEND})",
    )
    p.add_argument(
        "--skip-frontend", action="store_true",
        help="Vercel 프론트엔드 검증 생략",
    )

    args = parser.parse_args()
    {
        "prepare":   cmd_prepare,
        "screen":    cmd_screen,
        "narrate":   cmd_narrate,
        "review":    cmd_review,
        "preflight": cmd_preflight,
        "commit":    cmd_commit,
        "verify":    cmd_verify,
    }[args.cmd](args)


if __name__ == "__main__":
    main()
