import type { InterestPriceRange } from "@/types/schema";
import { formatPrice } from "@/lib/formatters";

interface InterestRangeSectionProps {
  range: InterestPriceRange;
  currentPrice: number;
}

export function InterestRangeSection({ range, currentPrice }: InterestRangeSectionProps) {
  if (range.status === "UNAVAILABLE") {
    return (
      <div className="bg-bg-surface border border-border-default rounded-lg p-4">
        <h3 className="text-sm font-medium text-text-primary mb-2">관심 가격 구간</h3>
        <p className="text-xs text-text-muted">데이터 불충분으로 산출 불가</p>
      </div>
    );
  }

  const isInRange =
    range.lower_bound !== null &&
    range.upper_bound !== null &&
    currentPrice >= range.lower_bound &&
    currentPrice <= range.upper_bound;

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <h3 className="text-sm font-medium text-text-primary">관심 가격 구간</h3>
        <span className="text-[10px] text-text-muted border border-border-default rounded px-1.5 py-0.5">
          목표주가 아님
        </span>
        {isInRange && (
          <span className="text-[10px] text-accent-gold border border-yellow-800 bg-yellow-950 rounded px-1.5 py-0.5">
            현재가 구간 내
          </span>
        )}
      </div>

      {range.lower_bound !== null && range.upper_bound !== null && (
        <div className="flex items-center gap-3 mb-3">
          <div className="font-mono text-xl font-bold text-accent-gold">
            {formatPrice(range.lower_bound)} — {formatPrice(range.upper_bound)}
          </div>
        </div>
      )}

      <p className="text-xs text-text-secondary leading-relaxed mb-3">
        {range.conditional_statement}
      </p>

      <div className="bg-bg-overlay border border-border-default rounded p-2.5">
        <p className="text-[10px] text-text-muted leading-relaxed">
          ⚠️ {range.disclaimer}
        </p>
      </div>

      {range.basis_metric && range.basis_sector_median_value && (
        <div className="mt-2 text-[10px] text-text-muted">
          산출 기준: {range.basis_metric} 섹터 중앙값 {range.basis_sector_median_value}배 적용
        </div>
      )}
    </div>
  );
}
