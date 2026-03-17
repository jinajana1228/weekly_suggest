import Link from "next/link";
import type { StockCard as StockCardType } from "@/types/schema";
import { CatalystBadgeGroup } from "./badges/CatalystBadge";
import { RiskLevelBadge } from "./badges/RiskLevelBadge";
import { SignalBadge } from "./badges/SignalBadge";
import { formatPrice, formatBillion } from "@/lib/formatters";

interface StockCardProps {
  stock: StockCardType;
  reportId: string;
  dataAsOf?: string;
}

export function StockCard({ stock, reportId }: StockCardProps) {
  const hasDataWarning = stock.data_quality_summary.highest_severity === "WARNING";
  const discountPct = stock.valuation_signal.sector_discount_pct;

  return (
    <Link
      href={`/report/${stock.report_item_id}?report_id=${reportId}`}
      className="block group"
    >
      <div className="bg-bg-surface border border-border-default rounded-lg hover:border-zinc-600 hover:bg-bg-elevated transition-all duration-150">
        <div className="px-5 py-4">
          {/* 헤더 행 */}
          <div className="flex items-start justify-between gap-3 mb-2.5">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-0.5">
                <span className="font-mono font-bold text-text-primary text-base tracking-wide">
                  {stock.ticker}
                </span>
                <span className="text-[10px] text-text-muted border border-border-default rounded px-1.5 py-0.5 leading-none">
                  {stock.exchange}
                </span>
                {hasDataWarning && (
                  <span className="text-[10px] text-yellow-600 border border-yellow-900 rounded px-1.5 py-0.5 leading-none bg-yellow-950/40">
                    데이터 주의
                  </span>
                )}
              </div>
              <p className="text-sm font-medium text-text-secondary truncate">{stock.company_name}</p>
              <p className="text-xs text-text-muted mt-0.5 truncate">
                {stock.sector}
                {stock.industry ? ` · ${stock.industry}` : ""}
              </p>
            </div>

            {/* 가격 + 할인율 */}
            <div className="text-right shrink-0">
              <div className="font-mono text-lg font-semibold text-text-primary tabular-nums">
                {formatPrice(stock.current_price.value)}
              </div>
              <div className="text-xs text-text-muted tabular-nums">{formatBillion(stock.market_cap_usd_b)}</div>
              {discountPct != null && discountPct > 0 && (
                <div className="text-[10px] text-accent-gold mt-0.5 tabular-nums">
                  -{discountPct.toFixed(0)}% vs 섹터
                </div>
              )}
            </div>
          </div>

          {/* 한 줄 논거 */}
          <p className="text-xs text-text-secondary leading-relaxed mb-3 line-clamp-2 min-h-[2.5em]">
            {stock.one_line_thesis}
          </p>

          {/* 하단 배지 행 */}
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 flex-wrap">
              <SignalBadge
                signal={stock.valuation_signal.signal_label}
                discountPct={stock.valuation_signal.sector_discount_pct}
              />
              <CatalystBadgeGroup badges={stock.catalyst_badges} />
            </div>
            <div className="flex items-center gap-2">
              <RiskLevelBadge level={stock.risk_level_overall} />
              <span className="text-xs text-text-muted group-hover:text-text-secondary transition-colors">→</span>
            </div>
          </div>
        </div>
      </div>
    </Link>
  );
}
