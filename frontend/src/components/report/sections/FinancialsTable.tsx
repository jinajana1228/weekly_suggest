import type { StockReport } from "@/types/schema";
import { formatBillion, formatPct, formatMultiple } from "@/lib/formatters";
import { DataValueDisplay } from "../badges/DataStatusBadge";
import { REVISION_TREND_LABELS } from "@/lib/constants";

interface FinancialsTableProps {
  report: StockReport;
}

export function FinancialsTable({ report }: FinancialsTableProps) {
  const { financials } = report;
  const trendConfig = REVISION_TREND_LABELS[financials.eps_revision_trend] || REVISION_TREND_LABELS.UNAVAILABLE;

  const rows = [
    {
      label: "매출 (TTM)",
      value: <DataValueDisplay value={financials.revenue_ttm_b} formatter={(v) => formatBillion(v)} className="text-sm text-text-primary" />,
    },
    {
      label: "매출 성장 (YoY)",
      value: <DataValueDisplay value={financials.revenue_growth_yoy_pct} formatter={(v) => formatPct(v)} className={`text-sm ${financials.revenue_growth_yoy_pct?.value !== null && (financials.revenue_growth_yoy_pct?.value ?? 0) >= 0 ? "text-accent-green" : "text-accent-red"}`} />,
    },
    {
      label: "영업이익 (TTM)",
      value: <DataValueDisplay value={financials.operating_income_ttm_b} formatter={(v) => formatBillion(v)} className="text-sm text-text-primary" />,
    },
    {
      label: "영업이익률",
      value: <DataValueDisplay value={financials.operating_margin_pct} formatter={(v) => formatPct(v, false)} className="text-sm text-text-primary" />,
    },
    {
      label: "EPS (TTM)",
      value: <DataValueDisplay value={financials.eps_ttm} formatter={(v) => v ? `$${v.toFixed(2)}` : "—"} className="text-sm text-text-primary" />,
    },
    {
      label: "Fwd EPS (컨센서스)",
      value: <DataValueDisplay value={financials.eps_fwd_consensus} formatter={(v) => v ? `$${v.toFixed(2)}` : "—"} className="text-sm text-text-primary" />,
    },
    {
      label: "EPS 컨센서스 추세",
      value: <span className={`text-sm font-medium ${trendConfig.color}`}>{trendConfig.label}</span>,
    },
    {
      label: "FCF (TTM)",
      value: <DataValueDisplay value={financials.fcf_ttm_b} formatter={(v) => formatBillion(v)} className="text-sm text-text-primary" />,
    },
    {
      label: "순부채/EBITDA",
      value: <DataValueDisplay value={financials.net_debt_to_ebitda} formatter={(v) => formatMultiple(v)} className="text-sm text-text-primary" />,
    },
    {
      label: "이자보상배율",
      value: <DataValueDisplay value={financials.interest_coverage_ratio} formatter={(v) => formatMultiple(v)} className="text-sm text-text-primary" />,
    },
    {
      label: "ROE",
      value: <DataValueDisplay value={financials.roe_pct} formatter={(v) => formatPct(v, false)} className="text-sm text-text-primary" />,
    },
  ];

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-border-default flex items-center justify-between">
        <h3 className="text-sm font-medium text-text-primary">핵심 재무 지표</h3>
        <span className="text-xs text-text-muted">{financials.fiscal_year}</span>
      </div>
      <div className="divide-y divide-border-default">
        {rows.map((row, i) => (
          <div key={i} className="flex items-center justify-between px-4 py-2.5">
            <span className="text-xs text-text-muted">{row.label}</span>
            {row.value}
          </div>
        ))}
      </div>
    </div>
  );
}
