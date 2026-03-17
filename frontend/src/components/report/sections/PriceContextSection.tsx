import type { StockReport } from "@/types/schema";
import { formatPrice, formatPct, getPctColor } from "@/lib/formatters";
import { DataValueDisplay } from "../badges/DataStatusBadge";

interface PriceContextSectionProps {
  report: StockReport;
}

export function PriceContextSection({ report }: PriceContextSectionProps) {
  const { current_price, price_context } = report;

  const metrics = [
    { label: "1개월 수익률", value: price_context.price_1m_change_pct },
    { label: "3개월 수익률", value: price_context.price_3m_change_pct },
    { label: "6개월 수익률", value: price_context.price_6m_change_pct },
    { label: "YTD 수익률", value: price_context.price_ytd_change_pct },
    { label: "52주 고점 대비", value: price_context.drawdown_from_52w_high_pct },
  ];

  // 52주 범위 내 위치 계산
  const high52 = price_context.week_52_high.value;
  const low52 = price_context.week_52_low.value;
  const positionPct = price_context.week_52_position_pct.value;

  return (
    <div className="space-y-4">
      {/* 현재가 + 52주 범위 */}
      <div className="bg-bg-surface rounded-lg border border-border-default p-4">
        <div className="flex items-start justify-between gap-4 mb-4">
          <div>
            <div className="font-mono text-3xl font-bold text-text-primary">
              {formatPrice(current_price.value)}
            </div>
            <div className="text-xs text-text-muted mt-1">
              기준일: {new Date(current_price.as_of).toLocaleDateString("ko-KR")}
            </div>
          </div>
          <div className="text-right">
            <div className="text-xs text-text-muted mb-1">시가총액</div>
            <div className="font-mono text-sm text-text-secondary">${report.stock_info.market_cap_usd_b.toFixed(1)}B</div>
          </div>
        </div>

        {/* 52주 바 */}
        {high52 && low52 && positionPct !== null && (
          <div>
            <div className="flex items-center justify-between text-[10px] text-text-muted mb-1.5">
              <span className="font-mono">${low52} (52주 저점)</span>
              <span className="font-mono">${high52} (52주 고점)</span>
            </div>
            <div className="relative h-2 bg-bg-overlay rounded-full overflow-hidden border border-border-default">
              <div
                className="absolute left-0 top-0 h-full bg-gradient-to-r from-accent-red/30 to-accent-green/30 rounded-full"
                style={{ width: "100%" }}
              />
              <div
                className="absolute top-0 w-3 h-full flex items-center justify-center"
                style={{ left: `calc(${Math.min(Math.max(positionPct, 2), 98)}% - 6px)` }}
              >
                <div className="w-2 h-2 rounded-full bg-accent-gold border-2 border-bg-base shadow" />
              </div>
            </div>
            <div className="text-center text-[10px] text-text-muted mt-1">
              52주 범위 내 {positionPct.toFixed(1)}% 위치
            </div>
          </div>
        )}
      </div>

      {/* 수익률 그리드 */}
      <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
        {metrics.map((m) => (
          <div key={m.label} className="bg-bg-surface border border-border-default rounded-lg p-3 text-center">
            <div className="text-[10px] text-text-muted mb-1">{m.label}</div>
            <DataValueDisplay
              value={m.value}
              formatter={(v) => formatPct(v)}
              className={`text-sm ${m.value?.value !== null && m.value?.value !== undefined ? getPctColor(m.value.value) : "text-text-muted"}`}
            />
          </div>
        ))}
      </div>
    </div>
  );
}
