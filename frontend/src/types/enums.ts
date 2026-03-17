export type PublishStatus = "DRAFT" | "PENDING_REVIEW" | "APPROVED" | "PUBLISHED" | "ARCHIVED" | "WITHDRAWN";

export type DataStatus = "CONFIRMED" | "UNVERIFIED" | "UNAVAILABLE" | "NOT_APPLICABLE" | "STALE";

export type CatalystStatus = "MET" | "NOT_MET" | "UNVERIFIABLE" | "NOT_ASSESSED";

export type UndervaluationSignal = "STRONG_SIGNAL" | "MODERATE_SIGNAL" | "WEAK_SIGNAL" | "NO_SIGNAL" | "INSUFFICIENT_DATA";

export type RiskLevel = "HIGH" | "MEDIUM" | "LOW" | "UNASSESSED";

export type RiskCategory =
  | "COMPETITIVE"
  | "FINANCIAL_HEALTH"
  | "OPERATIONAL"
  | "REGULATORY"
  | "MACRO_SENSITIVITY"
  | "EARNINGS_RISK"
  | "LIQUIDITY"
  | "GOVERNANCE";

export type IssueType = "REGULAR_BIWEEKLY" | "EARNINGS_TRIGGERED" | "SPECIAL_EVENT";

export type EpsRevisionTrend = "UPWARD" | "STABLE" | "DOWNWARD" | "UNAVAILABLE";

export type NarrativeStatus = "GENERATED" | "UNDER_REVIEW" | "APPROVED" | "FLAGGED_FOR_REVISION" | "PLACEHOLDER";

export type DataFlagType =
  | "MISSING_FIELD"
  | "STALE_DATA"
  | "LOW_CONFIDENCE"
  | "CROSS_SOURCE_MISMATCH"
  | "MANUAL_OVERRIDE_APPLIED";

export type ConfidenceLevel = "HIGH" | "MEDIUM" | "LOW";

export type ExchangeCode = "NYSE" | "NASDAQ" | "AMEX";

export type ReviewItemStatus = "PENDING" | "APPROVED" | "FLAGGED" | "REJECTED";

export type ReviewTaskStatus = "OPEN" | "IN_PROGRESS" | "COMPLETED" | "ESCALATED";
