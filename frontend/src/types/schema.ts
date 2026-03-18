import type {
  PublishStatus,
  DataStatus,
  CatalystStatus,
  UndervaluationSignal,
  RiskLevel,
  RiskCategory,
  IssueType,
  EpsRevisionTrend,
  NarrativeStatus,
  DataFlagType,
  ConfidenceLevel,
  ExchangeCode,
  ReviewItemStatus,
  ReviewTaskStatus,
} from "./enums";

// ─── 공통 래퍼 ────────────────────────────────────────────
export interface DataValue<T> {
  value: T | null;
  status: DataStatus;
}

export interface DisclaimerBlock {
  block_id: string;
  position: "HEADER" | "FOOTER" | "INLINE";
  content: string;
  is_required: boolean;
}

export interface DataSource {
  source_id: string;
  provider_name: string;
  data_category: string;
  as_of: string;
}

export interface DataQualityFlag {
  flag_id: string;
  field_path: string;
  flag_type: DataFlagType;
  message: string;
  severity: "WARNING" | "INFO";
}

// ─── 가격 ────────────────────────────────────────────────
export interface PricePoint {
  value: number;
  currency: string;
  as_of: string;
}

export interface PriceContext {
  week_52_high: DataValue<number>;
  week_52_low: DataValue<number>;
  week_52_position_pct: DataValue<number>;
  drawdown_from_52w_high_pct: DataValue<number>;
  price_1m_change_pct: DataValue<number>;
  price_3m_change_pct: DataValue<number>;
  price_6m_change_pct: DataValue<number>;
  price_ytd_change_pct: DataValue<number>;
  as_of: string;
}

export interface InterestPriceRange {
  status: DataStatus;
  lower_bound: number | null;
  upper_bound: number | null;
  basis_metric: string | null;
  basis_sector_median_value: number | null;
  conditional_statement: string;
  disclaimer: string;
}

// ─── 밸류에이션 ──────────────────────────────────────────
export interface ValuationMetrics {
  fwd_per: DataValue<number>;
  trailing_per: DataValue<number>;
  ev_ebitda: DataValue<number>;
  pb: DataValue<number>;
  ps: DataValue<number>;
  p_fcf: DataValue<number>;
}

export interface SectorDiscount {
  status: DataStatus;
  metric_used: string | null;
  stock_value: number | null;
  sector_median_value: number | null;
  discount_pct: number | null;
  sector_comparison_name: string | null;
  comparison_universe_count: number | null;
}

export interface HistoricalValuationPosition {
  status: DataStatus;
  metric_used: string | null;
  current_value: number | null;
  three_year_mean: number | null;
  three_year_min: number | null;
  three_year_max: number | null;
  percentile_rank: number | null;
}

export interface Valuation {
  primary_metric: string;
  metrics: ValuationMetrics;
  valuation_discount_vs_sector: SectorDiscount;
  historical_valuation_position: HistoricalValuationPosition;
}

// ─── 재무 ────────────────────────────────────────────────
export interface Financials {
  status: DataStatus;
  fiscal_year: string;
  revenue_ttm_b: DataValue<number>;
  revenue_growth_yoy_pct: DataValue<number>;
  operating_income_ttm_b: DataValue<number>;
  operating_margin_pct: DataValue<number>;
  net_income_ttm_b: DataValue<number>;
  eps_ttm: DataValue<number>;
  eps_fwd_consensus: DataValue<number>;
  eps_revision_trend: EpsRevisionTrend;
  fcf_ttm_b: DataValue<number>;
  net_debt_b: DataValue<number>;
  net_debt_to_ebitda: DataValue<number>;
  interest_coverage_ratio: DataValue<number>;
  roe_pct: DataValue<number>;
}

// ─── 저평가 판단 ──────────────────────────────────────────
export interface NarrativeBlock {
  content: string;
  status: NarrativeStatus;
  data_fields_referenced: string[];
}

export interface UndervaluationJudgment {
  is_discounted_vs_sector: boolean;
  is_discounted_vs_history: boolean;
  combined_signal: UndervaluationSignal;
  primary_discount_drivers: string[];
  discount_narrative: NarrativeBlock;
}

// ─── 촉매 ────────────────────────────────────────────────
export interface CatalystDetail {
  catalyst_id: "A" | "B" | "C";
  definition_summary: string;
  status: CatalystStatus;
  evidence: string | null;
  data_status: DataStatus;
}

export interface CatalystAssessment {
  catalyst_a: CatalystDetail;
  catalyst_b: CatalystDetail;
  catalyst_c: CatalystDetail;
  met_count: number;
  composite_label: string;
}

// ─── Bull/Bear ───────────────────────────────────────────
export interface BullBearPoint {
  point_id: number;
  summary: string;
  detail: string;
  confidence: ConfidenceLevel;
  is_data_backed: boolean;
}

// ─── 리스크 ──────────────────────────────────────────────
export interface RiskItem {
  risk_id: string;
  category: RiskCategory;
  label: string;
  description: string;
  severity: RiskLevel;
  data_status: DataStatus;
}

// ─── LLM 서술 ────────────────────────────────────────────
export interface AnalystStyleSummary {
  why_discounted: NarrativeBlock;
  why_worth_revisiting: NarrativeBlock;
  key_risks_narrative: NarrativeBlock;
  investment_context: NarrativeBlock;
  generated_at: string;
  model_id: string;
  reviewer_approved: boolean;
}

// ─── Stock Card (리스트 요약 뷰) ──────────────────────────
export interface CatalystBadge {
  catalyst_id: "A" | "B" | "C";
  status: CatalystStatus;
}

export interface ValuationSignalSummary {
  sector_discount_pct: number;
  signal_label: UndervaluationSignal;
}

export interface DataQualitySummary {
  flag_count: number;
  highest_severity: "WARNING" | "INFO" | "NONE";
}

export interface StockCard {
  report_item_id: string;
  ticker: string;
  company_name: string;
  exchange: ExchangeCode;
  sector: string;
  industry?: string;
  current_price: PricePoint;
  market_cap_usd_b: number;
  one_line_thesis: string;
  valuation_signal: ValuationSignalSummary;
  catalyst_badges: CatalystBadge[];
  risk_level_overall: RiskLevel;
  data_quality_summary: DataQualitySummary;
  selection_type?: import("./enums").SelectionType;
}

// ─── Report Edition ──────────────────────────────────────
export interface ReportEdition {
  report_id: string;
  edition_number: number;
  issue_type: IssueType;
  status: PublishStatus;
  published_at: string | null;
  data_as_of: string;
  market_context_note: string | null;
  screening_run_id: string;
  stocks: StockCard[];
  disclaimer_blocks: DisclaimerBlock[];
  created_at: string;
  last_updated_at: string;
}

// ─── Stock Detail Report ─────────────────────────────────
export interface StockInfo {
  short_description: string;
  headquarters: string | null;
  market_cap_usd_b: number;
  employee_count: DataValue<number>;
  fiscal_year_end: string;
}

export interface PublicationMeta {
  status: PublishStatus;
  created_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
  published_at: string | null;
  last_updated_at: string;
}

export interface StockReport {
  report_item_id: string;
  report_id: string;
  ticker: string;
  company_name: string;
  exchange: ExchangeCode;
  sector: string;
  industry: string;
  stock_info: StockInfo;
  current_price: PricePoint;
  price_context: PriceContext;
  interest_price_range: InterestPriceRange;
  valuation: Valuation;
  financials: Financials;
  undervaluation_judgment: UndervaluationJudgment;
  catalyst_assessment: CatalystAssessment;
  bull_case_points: BullBearPoint[];
  bear_case_points: BullBearPoint[];
  structural_risks: RiskItem[];
  short_term_risks: RiskItem[];
  analyst_style_summary: AnalystStyleSummary;
  data_quality_flags: DataQualityFlag[];
  data_sources: DataSource[];
  disclaimer_blocks: DisclaimerBlock[];
  publication_meta: PublicationMeta;
}

// ─── Archive ─────────────────────────────────────────────
export interface ArchiveStockSummary {
  ticker: string;
  company_name: string;
  sector: string;
  one_line_thesis: string;
  risk_level_overall: RiskLevel;
  valuation_signal: ValuationSignalSummary;
  catalyst_badges: CatalystBadge[];
  report_item_id: string;
}

export interface ArchiveEntry {
  report_id: string;
  edition_number: number;
  issue_type: IssueType;
  status: PublishStatus;
  published_at: string | null;
  data_as_of: string;
  market_context_note: string | null;
  stock_count: number;
  stocks: ArchiveStockSummary[];
}

// ─── Chart ───────────────────────────────────────────────
export interface OHLCVPoint {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close: number;
}

export interface EventMarker {
  marker_id: string;
  date: string;
  event_type: string;
  label: string;
  detail: string | null;
  is_catalyst_related: boolean;
}

export interface ReferenceLine {
  line_id: string;
  line_type: string;
  value: number;
  label: string;
  style_hint?: string;
}

export interface InterestRangeBand {
  lower_bound: number;
  upper_bound: number;
  label: string;
  conditional_note: string;
}

export interface ChartDataPackage {
  ticker: string;
  chart_as_of: string;
  period_days: number;
  price_series: OHLCVPoint[];
  event_markers: EventMarker[];
  reference_lines: ReferenceLine[];
  interest_range_band: InterestRangeBand | null;
}

// ─── Admin / Review ──────────────────────────────────────
export interface ReviewItem {
  report_item_id: string;
  ticker: string;
  review_status: ReviewItemStatus;
  reviewer_notes: string | null;
  data_quality_flag_count: number;
  llm_narrative_approved: boolean;
}

export interface ReviewTask {
  review_task_id: string;
  report_id: string;
  status: ReviewTaskStatus;
  assigned_to: string | null;
  created_at: string;
  completed_at: string | null;
  screening_summary: {
    total_candidates: number;
    selected_count: number;
    excluded_count: number;
    run_at: string;
    filters_applied: string[];
  };
  review_items: ReviewItem[];
  publish_decision: {
    decision: "APPROVE" | "REJECT" | "HOLD";
    decided_by: string;
    decided_at: string;
    reason: string | null;
  } | null;
}

// ─── API Response ─────────────────────────────────────────
export interface ApiResponse<T> {
  data: T;
}
