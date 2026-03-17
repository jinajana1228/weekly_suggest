import type { UndervaluationSignal, RiskLevel, CatalystStatus, DataStatus } from "@/types/enums";

export const SIGNAL_LABELS: Record<UndervaluationSignal, string> = {
  STRONG_SIGNAL: "강한 신호",
  MODERATE_SIGNAL: "중간 신호",
  WEAK_SIGNAL: "약한 신호",
  NO_SIGNAL: "신호 없음",
  INSUFFICIENT_DATA: "데이터 부족",
};

export const SIGNAL_COLORS: Record<UndervaluationSignal, string> = {
  STRONG_SIGNAL: "text-accent-blue border-blue-800 bg-blue-950",
  MODERATE_SIGNAL: "text-accent-gold border-yellow-800 bg-yellow-950",
  WEAK_SIGNAL: "text-text-secondary border-zinc-700 bg-zinc-900",
  NO_SIGNAL: "text-text-muted border-zinc-800 bg-zinc-950",
  INSUFFICIENT_DATA: "text-text-muted border-zinc-800 bg-zinc-950",
};

export const RISK_LABELS: Record<RiskLevel, string> = {
  HIGH: "높음",
  MEDIUM: "보통",
  LOW: "낮음",
  UNASSESSED: "미평가",
};

export const RISK_COLORS: Record<RiskLevel, string> = {
  HIGH: "text-accent-red bg-red-950 border-red-900",
  MEDIUM: "text-orange-400 bg-orange-950 border-orange-900",
  LOW: "text-accent-green bg-green-950 border-green-900",
  UNASSESSED: "text-text-muted bg-zinc-900 border-zinc-800",
};

export const CATALYST_LABELS: Record<CatalystStatus, string> = {
  MET: "충족",
  NOT_MET: "미충족",
  UNVERIFIABLE: "확인 불가",
  NOT_ASSESSED: "미평가",
};

export const CATALYST_COLORS: Record<CatalystStatus, string> = {
  MET: "text-accent-blue bg-blue-950 border-blue-800",
  NOT_MET: "text-text-muted bg-zinc-900 border-zinc-800",
  UNVERIFIABLE: "text-yellow-500 bg-yellow-950 border-yellow-900",
  NOT_ASSESSED: "text-text-muted bg-zinc-900 border-zinc-800",
};

export const DATA_STATUS_LABELS: Record<DataStatus, string> = {
  CONFIRMED: "확인됨",
  UNVERIFIED: "미검증",
  UNAVAILABLE: "데이터 없음",
  NOT_APPLICABLE: "해당 없음",
  STALE: "기간 초과",
};

export const REVISION_TREND_LABELS: Record<string, { label: string; color: string }> = {
  UPWARD: { label: "상향 추세", color: "text-accent-green" },
  STABLE: { label: "유지", color: "text-text-secondary" },
  DOWNWARD: { label: "하향 추세", color: "text-accent-red" },
  UNAVAILABLE: { label: "데이터 없음", color: "text-text-muted" },
};

export const RISK_CATEGORY_LABELS: Record<string, string> = {
  COMPETITIVE: "경쟁 리스크",
  FINANCIAL_HEALTH: "재무 건전성",
  OPERATIONAL: "운영 리스크",
  REGULATORY: "규제 리스크",
  MACRO_SENSITIVITY: "거시 민감도",
  EARNINGS_RISK: "실적 리스크",
  LIQUIDITY: "유동성",
  GOVERNANCE: "지배구조",
};
