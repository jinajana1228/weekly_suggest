import type { RiskItem } from "@/types/schema";
import { RiskLevelBadge } from "../badges/RiskLevelBadge";
import { RISK_CATEGORY_LABELS } from "@/lib/constants";

interface RiskSectionProps {
  structuralRisks: RiskItem[];
  shortTermRisks: RiskItem[];
}

function RiskCard({ risk }: { risk: RiskItem }) {
  return (
    <div className="bg-bg-surface border border-border-default rounded-lg p-3.5">
      <div className="flex items-start justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-medium text-text-primary">{risk.label}</span>
          <span className="text-[10px] text-text-muted bg-bg-overlay border border-border-default rounded px-1.5 py-0.5">
            {RISK_CATEGORY_LABELS[risk.category] || risk.category}
          </span>
        </div>
        <div className="shrink-0">
          <RiskLevelBadge level={risk.severity} />
        </div>
      </div>
      <p className="text-xs text-text-secondary leading-relaxed">{risk.description}</p>
    </div>
  );
}

export function RiskSection({ structuralRisks, shortTermRisks }: RiskSectionProps) {
  return (
    <div className="space-y-4">
      {/* 구조적 리스크 */}
      <div>
        <div className="flex items-center gap-2 mb-2.5">
          <div className="w-1 h-4 bg-accent-red rounded-full opacity-60" />
          <h3 className="text-sm font-medium text-text-primary">구조적 리스크</h3>
          <span className="text-xs text-text-muted">(중장기 펀더멘털)</span>
        </div>
        <div className="space-y-2">
          {structuralRisks.map((r) => <RiskCard key={r.risk_id} risk={r} />)}
        </div>
      </div>

      {/* 단기 리스크 */}
      <div>
        <div className="flex items-center gap-2 mb-2.5">
          <div className="w-1 h-4 bg-orange-500 rounded-full opacity-60" />
          <h3 className="text-sm font-medium text-text-primary">단기 리스크</h3>
          <span className="text-xs text-text-muted">(3개월 내 촉발 가능)</span>
        </div>
        <div className="space-y-2">
          {shortTermRisks.map((r) => <RiskCard key={r.risk_id} risk={r} />)}
        </div>
      </div>
    </div>
  );
}
