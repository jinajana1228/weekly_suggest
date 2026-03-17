"""
Narrative 자동 생성 — Claude API를 사용해 4개 NarrativeBlock을 생성.

생성 대상:
  - why_discounted       : 시장 할인 원인 분석
  - why_worth_revisiting : 리레이팅 근거
  - key_risks_narrative  : 핵심 리스크 종합
  - investment_context   : 투자 맥락 요약

엄격 제약:
  - 제공된 구조화 데이터의 수치만 참조 (새 숫자 생성 금지)
  - 목표주가, 매수/매도 권고, 수익 보장 표현 금지
  - 각 블록 2~3문장, 한국어

API 키 없거나 호출 실패 시 → graceful fallback (PLACEHOLDER 상태 반환)
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── 시스템 프롬프트 ───────────────────────────────────────────────

_SYSTEM_PROMPT = """당신은 미국 주식 시장 분석 보조 AI입니다.
제공된 구조화된 JSON 데이터만을 참조하여 4개의 분석 서술 블록을 작성합니다.

엄격한 제약:
1. 제공된 데이터에 있는 수치 외에 새로운 숫자를 절대 생성하지 마세요.
2. 목표주가, 매수/매도 추천, 수익 보장 표현은 절대 사용하지 마세요.
3. 불확실한 데이터는 "~로 추정" 또는 "확인 불가" 등으로 명확히 구분하세요.
4. 각 블록은 한국어로 2~3문장(60~130자)으로 작성하세요.
5. 데이터에 근거하지 않은 추측성 서술을 하지 마세요.
6. 반드시 아래 JSON 형식으로만 응답하세요."""

_USER_TEMPLATE = """아래 종목 데이터를 분석하여 4개 블록을 생성하세요.

## 종목 요약
- 티커: {ticker}
- 기업명: {company_name}
- 섹터: {sector} / 업종: {industry}
- 현재가: {current_price} USD
- 시총: {market_cap}B USD

## 밸류에이션
- 기준 지표: {primary_metric}
- 섹터 대비 할인율: {discount_pct}%
- 현재 지표값: {metric_value}
- 섹터 중앙값: {sector_median}

## 촉매 (3가지)
- A (어닝 일정): {cat_a}
- B (컨센서스 갭): {cat_b}
- C (52주 위치): {cat_c}
- 충족 수: {met_count}/3

## 리스크
- 종합 리스크: {risk_level}
- 구조적 리스크: {structural_risks}
- 단기 리스크: {short_term_risks}

## 강세/약세 포인트
- 강세: {bull_points}
- 약세: {bear_points}

위 데이터를 바탕으로 아래 JSON 형식으로 응답하세요:
{{
  "why_discounted": "왜 시장이 이 종목을 할인하고 있는지 2~3문장",
  "why_worth_revisiting": "왜 지금 이 종목을 다시 검토할 가치가 있는지 2~3문장",
  "key_risks_narrative": "핵심 리스크 2~3가지를 통합하여 2~3문장",
  "investment_context": "이 종목의 현재 투자 맥락을 종합적으로 2~3문장"
}}"""


# ── 헬퍼 함수 ─────────────────────────────────────────────────────

def _dv(obj: dict | None, key: str = "value", default="N/A"):
    """DataValue dict에서 value 추출."""
    if obj is None:
        return default
    v = obj.get(key)
    return v if v is not None else default


def _extract_context(report: dict) -> dict:
    """StockReport에서 narrative 생성에 필요한 핵심 필드만 추출."""
    valuation = report.get("valuation", {})
    discount = valuation.get("valuation_discount_vs_sector", {})
    cat = report.get("catalyst_assessment", {})
    cat_a = cat.get("catalyst_a", {})
    cat_b = cat.get("catalyst_b", {})
    cat_c = cat.get("catalyst_c", {})

    structural = report.get("structural_risks", [])
    short_term = report.get("short_term_risks", [])
    bull = report.get("bull_case_points", [])
    bear = report.get("bear_case_points", [])

    price = report.get("current_price", {})

    def risk_desc(risks: list) -> str:
        items = [r.get("label", r.get("description", "")) for r in risks[:3]]
        return ", ".join(items) if items else "N/A"

    def case_desc(cases: list) -> str:
        items = [c.get("summary", "") for c in cases[:3]]
        return " / ".join(items) if items else "N/A"

    return {
        "ticker": report.get("ticker", ""),
        "company_name": report.get("company_name", ""),
        "sector": report.get("sector", ""),
        "industry": report.get("industry", ""),
        "current_price": f"{_dv(price):.2f}" if isinstance(_dv(price), float) else str(_dv(price)),
        "market_cap": report.get("market_cap_usd_b", report.get("stock_info", {}).get("market_cap_usd_b", "N/A")),
        "primary_metric": valuation.get("primary_metric", "N/A"),
        "discount_pct": discount.get("discount_pct", "N/A"),
        "metric_value": discount.get("stock_value", "N/A"),
        "sector_median": discount.get("sector_median_value", "N/A"),
        "cat_a": f"{cat_a.get('status', 'N/A')} — {cat_a.get('description', '')}",
        "cat_b": f"{cat_b.get('status', 'N/A')} — {cat_b.get('description', '')}",
        "cat_c": f"{cat_c.get('status', 'N/A')} — {cat_c.get('description', '')}",
        "met_count": cat.get("met_count", 0),
        "risk_level": max(
            (r.get("severity", "LOW") for r in structural + short_term),
            key=lambda x: {"HIGH": 3, "MEDIUM": 2, "LOW": 1}.get(x, 0),
            default="LOW",
        ),
        "structural_risks": risk_desc(structural),
        "short_term_risks": risk_desc(short_term),
        "bull_points": case_desc(bull),
        "bear_points": case_desc(bear),
    }


def _placeholder_block(reason: str = "API 키 미설정 또는 생성 실패") -> dict:
    return {
        "content": f"서술 자동 생성이 비활성화되어 있습니다. ({reason})",
        "status": "PLACEHOLDER",
        "data_fields_referenced": [],
    }


def _make_block(content: str, fields: list[str] | None = None) -> dict:
    return {
        "content": content,
        "status": "GENERATED",
        "data_fields_referenced": fields or [],
    }


# ── 메인 생성 함수 ────────────────────────────────────────────────

def generate_narrative(report: dict) -> dict:
    """
    StockReport dict → analyst_style_summary dict 생성.

    ANTHROPIC_API_KEY가 없거나 호출 실패 시 PLACEHOLDER 반환.

    Returns:
        {
          "why_discounted": NarrativeBlock,
          "why_worth_revisiting": NarrativeBlock,
          "key_risks_narrative": NarrativeBlock,
          "investment_context": NarrativeBlock,
          "generated_at": str,
          "model_id": str,
          "reviewer_approved": False,
        }
    """
    now = datetime.now(timezone.utc).isoformat()
    model_id = settings.NARRATIVE_MODEL

    if not settings.ANTHROPIC_API_KEY:
        logger.info("ANTHROPIC_API_KEY 미설정 — PLACEHOLDER 반환")
        return _placeholder_summary("ANTHROPIC_API_KEY 미설정", now)

    ctx = _extract_context(report)
    user_prompt = _USER_TEMPLATE.format(**ctx)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        message = client.messages.create(
            model=model_id,
            max_tokens=1024,
            system=_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_prompt}],
        )
        raw = message.content[0].text.strip()

        # JSON 파싱
        # Claude가 ```json ... ``` 블록으로 감쌀 수 있으므로 제거
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        data = json.loads(raw)

        fields_ref = [
            "valuation.valuation_discount_vs_sector",
            "catalyst_assessment",
            "structural_risks",
            "short_term_risks",
        ]

        return {
            "why_discounted": _make_block(data["why_discounted"], fields_ref),
            "why_worth_revisiting": _make_block(data["why_worth_revisiting"], fields_ref),
            "key_risks_narrative": _make_block(data["key_risks_narrative"], ["structural_risks", "short_term_risks"]),
            "investment_context": _make_block(data["investment_context"], fields_ref),
            "generated_at": now,
            "model_id": model_id,
            "reviewer_approved": False,
        }

    except ImportError:
        logger.warning("anthropic 패키지 미설치 — pip install anthropic>=0.34.0")
        return _placeholder_summary("anthropic 패키지 미설치", now)
    except json.JSONDecodeError as e:
        logger.error("Narrative JSON 파싱 실패: %s", e)
        return _placeholder_summary(f"JSON 파싱 오류: {e}", now)
    except Exception as e:
        logger.error("Narrative 생성 실패: %s", e)
        return _placeholder_summary(f"생성 실패: {type(e).__name__}", now)


def _placeholder_summary(reason: str, now: str) -> dict:
    ph = _placeholder_block(reason)
    return {
        "why_discounted": ph,
        "why_worth_revisiting": ph,
        "key_risks_narrative": ph,
        "investment_context": ph,
        "generated_at": now,
        "model_id": "placeholder",
        "reviewer_approved": False,
    }


# ── 배치 생성 (여러 종목) ─────────────────────────────────────────

def generate_narratives_for_reports(
    reports: list[dict],
    *,
    overwrite_existing: bool = False,
) -> dict[str, dict]:
    """
    여러 종목 StockReport → ticker별 narrative 생성.

    Parameters
    ----------
    reports           : StockReport dict 리스트
    overwrite_existing: True이면 PLACEHOLDER/GENERATED 여부 무관 재생성

    Returns
    -------
    dict[ticker, analyst_style_summary]
    """
    results = {}
    for report in reports:
        ticker = report.get("ticker", "UNKNOWN")
        existing = report.get("analyst_style_summary", {})

        # 이미 GENERATED이고 overwrite 아니면 스킵
        if not overwrite_existing:
            first_block = existing.get("why_discounted", {})
            if first_block.get("status") == "GENERATED":
                logger.info("%s: 이미 생성된 narrative 존재 — 스킵", ticker)
                results[ticker] = existing
                continue

        logger.info("%s: Narrative 생성 중...", ticker)
        results[ticker] = generate_narrative(report)

    return results
