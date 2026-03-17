import type { StockReport } from "@/types/schema";
import { formatMultiple, formatPct } from "@/lib/formatters";
import { DataValueDisplay } from "../badges/DataStatusBadge";

interface ValuationSectionProps {
  report: StockReport;
}

const METRIC_LABELS: Record<string, string> = {
  fwd_per: "Fwd PER",
  trailing_per: "Trailing PER",
  ev_ebitda: "EV/EBITDA",
  pb: "P/B",
  ps: "P/S",
  p_fcf: "P/FCF",
};

// display name → key 역매핑 (primary_metric 강조 표시에 사용)
const METRIC_KEY_BY_LABEL: Record<string, string> = Object.fromEntries(
  Object.entries(METRIC_LABELS).map(([k, v]) => [v, k])
);

export function ValuationSection({ report }: ValuationSectionProps) {
  const { valuation } = report;
  const { metrics, valuation_discount_vs_sector: sectorDiscount, historical_valuation_position: histPos } = valuation;

  const metricEntries = Object.entries(metrics) as [string, { value: number | null; status: string }][];

  return (
    <div className="space-y-4">
      {/* 밸류에이션 지표 테이블 */}
      <div className="bg-bg-surface border border-border-default rounded-lg overflow-hidden">
        <div className="px-4 py-3 border-b border-border-default">
          <h3 className="text-sm font-medium text-text-primary">밸류에이션 지표</h3>
          <p className="text-xs text-text-muted mt-0.5">주요 지표: {valuation.primary_metric}</p>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 divide-x divide-y divide-border-default">
          {metricEntries.map(([key, val]) => (
            <div key={key} className="p-3">
              <div className="text-[10px] text-text-muted uppercase tracking-wider mb-1">
                {METRIC_LABELS[key] || key}
                {key === (METRIC_KEY_BY_LABEL[valuation.primary_metric] ?? valuation.primary_metric) && (
                  <span className="ml-1 text-accent-gold">★</span>
                )}
              </div>
              <DataValueDisplay
                value={val as any}
                formatter={(v) => formatMultiple(v)}
                className="text-sm text-text-primary"
              />
            </div>
          ))}
        </div>
      </div>

      {/* 섹터 대비 할인 */}
      {sectorDiscount.status === "CONFIRMED" && sectorDiscount.discount_pct !== null && (
        <div className="bg-bg-surface border border-border-default rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-primary mb-3">섹터 대비 밸류에이션</h3>
          <div className="flex items-center gap-4 mb-3">
            <div className="text-center">
              <div className="text-[10px] text-text-muted mb-1">이 종목 ({sectorDiscount.metric_used})</div>
              <div className="font-mono text-2xl font-bold text-text-primary">
                {sectorDiscount.stock_value?.toFixed(1)}x
              </div>
            </div>
            <div className="flex-1 text-center">
              <div className="inline-flex items-center px-3 py-1.5 rounded bg-blue-950 border border-blue-800">
                <span className="font-mono text-accent-blue font-bold text-lg">
                  -{sectorDiscount.discount_pct.toFixed(1)}%
                </span>
              </div>
              <div className="text-[10px] text-text-muted mt-1">섹터 중앙값 대비 할인</div>
            </div>
            <div className="text-center">
              <div className="text-[10px] text-text-muted mb-1">섹터 중앙값</div>
              <div className="font-mono text-2xl font-bold text-text-secondary">
                {sectorDiscount.sector_median_value?.toFixed(1)}x
              </div>
            </div>
          </div>
          <p className="text-xs text-text-muted">
            비교 대상: {sectorDiscount.sector_comparison_name} ({sectorDiscount.comparison_universe_count}개 종목)
          </p>
        </div>
      )}

      {/* 히스토리 대비 위치 */}
      {histPos.status === "CONFIRMED" && histPos.percentile_rank !== null && (
        <div className="bg-bg-surface border border-border-default rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-primary mb-3">자사 3년 히스토리 대비 위치</h3>
          <div className="flex items-center gap-4 mb-3">
            {/* 히스토리 바 */}
            <div className="flex-1">
              <div className="flex items-center justify-between text-[10px] text-text-muted mb-1.5">
                <span>3년 최저 {histPos.three_year_min?.toFixed(1)}x</span>
                <span>3년 최고 {histPos.three_year_max?.toFixed(1)}x</span>
              </div>
              <div className="relative h-2 bg-bg-overlay rounded-full border border-border-default overflow-hidden">
                <div
                  className="absolute top-0 left-0 h-full bg-accent-blue/20 rounded-full"
                  style={{ width: `${histPos.percentile_rank}%` }}
                />
                <div
                  className="absolute top-0 w-2 h-2 rounded-full bg-accent-gold border-2 border-bg-base"
                  style={{ left: `calc(${Math.min(Math.max(histPos.percentile_rank, 2), 98)}% - 4px)` }}
                />
              </div>
              <div className="flex items-center justify-between text-[10px] text-text-muted mt-1">
                <span>저렴</span>
                <span className="text-accent-gold font-medium">하위 {histPos.percentile_rank}th percentile</span>
                <span>비쌈</span>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-2 text-center">
            {[
              { label: "현재", value: histPos.current_value },
              { label: "3년 평균", value: histPos.three_year_mean },
              { label: "3년 범위", value: null, range: [histPos.three_year_min, histPos.three_year_max] },
            ].map((item, i) => (
              <div key={i} className="bg-bg-overlay rounded p-2">
                <div className="text-[10px] text-text-muted mb-0.5">{item.label}</div>
                {item.range ? (
                  <div className="font-mono text-xs text-text-secondary">
                    {item.range[0]?.toFixed(1)}x ~ {item.range[1]?.toFixed(1)}x
                  </div>
                ) : (
                  <div className="font-mono text-sm font-bold text-text-primary">{item.value?.toFixed(1)}x</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
