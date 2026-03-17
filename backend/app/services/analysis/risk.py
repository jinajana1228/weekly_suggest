"""리스크 평가 엔진

2-레이어 구조:
  structural_risks  — 구조적/장기 리스크
  short_term_risks  — 단기(3개월) 리스크
"""
import uuid
from typing import Any


def assess_risks(snapshot: dict) -> tuple[list[dict], list[dict]]:
    """
    (structural_risks, short_term_risks) 반환.

    snapshot이 완전한 StockReport JSON이면 직접 반환.
    최소 스냅샷이면 섹터 기반 기본 리스크 생성.
    """
    if "structural_risks" in snapshot and "short_term_risks" in snapshot:
        return snapshot["structural_risks"], snapshot["short_term_risks"]

    return _compute_from_minimal(snapshot)


def _compute_from_minimal(snap: dict) -> tuple[list[dict], list[dict]]:
    """섹터/재무 정보 기반 기본 리스크 항목 생성 (real provider scaffold)."""
    sector = snap.get("sector", "")
    risk_level = snap.get("risk_level_max", "MEDIUM")

    structural = _build_structural_risks(sector, risk_level)
    short_term = _build_short_term_risks(sector, risk_level)

    return structural, short_term


def _rid() -> str:
    return f"r_{uuid.uuid4().hex[:8]}"


def _build_structural_risks(sector: str, risk_level: str) -> list[dict]:
    risks: list[dict] = []

    if sector == "Financials":
        risks.append(_risk(
            category="SECTOR_SPECIFIC",
            label="금리 사이클 리스크",
            description="고금리 장기화 시 NIM 압박 및 부실채권 증가 가능성.",
            severity="MEDIUM",
        ))
        risks.append(_risk(
            category="REGULATORY",
            label="자본 규제 강화",
            description="바젤 III 최종안 시행에 따른 자본비율 요건 상향 가능성.",
            severity="LOW",
        ))
    elif sector == "Energy":
        risks.append(_risk(
            category="SECTOR_SPECIFIC",
            label="유가 변동성",
            description="WTI 유가 급락 시 EBITDA 및 생산 가이던스 하향 조정 위험.",
            severity="HIGH" if risk_level == "HIGH" else "MEDIUM",
        ))
        risks.append(_risk(
            category="REGULATORY",
            label="탄소 규제 강화",
            description="중장기 탄소 감축 의무 강화로 E&P 투자 가치 하락 위험.",
            severity="MEDIUM",
        ))
    elif sector == "Health Care":
        risks.append(_risk(
            category="REGULATORY",
            label="의료 수가 개편",
            description="메디케어/메디케이드 수가 정책 변화로 매출 구조 영향 가능성.",
            severity="MEDIUM",
        ))
        risks.append(_risk(
            category="MARKET",
            label="경쟁 심화",
            description="디지털 헬스케어 기업의 시장 진입으로 시장점유율 압박.",
            severity="LOW",
        ))
    elif sector == "Consumer Staples":
        risks.append(_risk(
            category="MARKET",
            label="PB 제품 경쟁 심화",
            description="유통사 PB 제품 확대로 브랜드 프리미엄 유지에 압박.",
            severity="MEDIUM",
        ))
        risks.append(_risk(
            category="MACRO",
            label="원자재 비용 구조",
            description="농산물·포장재 가격 변동이 마진에 구조적으로 영향.",
            severity="LOW",
        ))
    else:
        risks.append(_risk(
            category="MARKET",
            label="경기 사이클 민감도",
            description="경기 침체 시 매출 및 마진 동반 하락 가능성.",
            severity=risk_level if risk_level in ("LOW", "MEDIUM", "HIGH") else "MEDIUM",
        ))

    return risks


def _build_short_term_risks(sector: str, risk_level: str) -> list[dict]:
    risks: list[dict] = []

    risks.append(_risk(
        category="EARNINGS",
        label="다음 실적 발표 불확실성",
        description="컨센서스 대비 실적 하회 시 단기 주가 변동성 확대 가능성.",
        severity="MEDIUM",
    ))

    if sector == "Energy":
        risks.append(_risk(
            category="MACRO",
            label="단기 유가 변동",
            description="지정학적 리스크 및 OPEC+ 결정에 따른 단기 유가 급변 가능성.",
            severity="HIGH" if risk_level == "HIGH" else "MEDIUM",
        ))
    elif sector == "Financials":
        risks.append(_risk(
            category="MACRO",
            label="연준 금리 결정 민감도",
            description="FOMC 통화정책 변화가 단기 주가에 직접 영향.",
            severity="MEDIUM",
        ))
    else:
        risks.append(_risk(
            category="MARKET",
            label="섹터 센티먼트 변화",
            description="섹터 내 악재 발생 시 동반 매도 압력 가능성.",
            severity="LOW",
        ))

    return risks


def _risk(category: str, label: str, description: str, severity: str) -> dict:
    return {
        "risk_id": _rid(),
        "category": category,
        "label": label,
        "description": description,
        "severity": severity,
        "data_status": "CONFIRMED",
    }
