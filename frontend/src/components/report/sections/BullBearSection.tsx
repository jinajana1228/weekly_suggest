import type { BullBearPoint } from "@/types/schema";

const CONFIDENCE_CONFIG: Record<string, { label: string; color: string }> = {
  HIGH: { label: "근거 충분", color: "text-accent-green" },
  MEDIUM: { label: "중간 근거", color: "text-yellow-500" },
  LOW: { label: "근거 낮음", color: "text-text-muted" },
};

interface BullBearSectionProps {
  bullCases: BullBearPoint[];
  bearCases: BullBearPoint[];
}

function CaseCard({ point, type }: { point: BullBearPoint; type: "bull" | "bear" }) {
  const conf = CONFIDENCE_CONFIG[point.confidence] || CONFIDENCE_CONFIG.MEDIUM;
  const dotColor = type === "bull" ? "bg-accent-green" : "bg-accent-red";

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg p-3.5 hover:border-zinc-700 transition-colors">
      <div className="flex items-start gap-2.5">
        <div className={`shrink-0 w-1.5 h-1.5 rounded-full mt-1.5 ${dotColor} opacity-70`} />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-text-primary leading-snug mb-1.5">
            {point.summary}
          </p>
          <p className="text-xs text-text-secondary leading-relaxed">{point.detail}</p>
          <div className="flex items-center gap-2 mt-2">
            <span className={`text-[10px] ${conf.color}`}>{conf.label}</span>
            {point.is_data_backed && (
              <span className="text-[10px] text-text-muted border border-border-default rounded px-1 py-0.5">
                수치 기반
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

export function BullBearSection({ bullCases, bearCases }: BullBearSectionProps) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
      {/* Bull Case */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-accent-green" />
          <h3 className="text-sm font-medium text-text-primary">강세 논거 (Bull Case)</h3>
        </div>
        <div className="space-y-2">
          {bullCases.map((p) => (
            <CaseCard key={p.point_id} point={p} type="bull" />
          ))}
        </div>
      </div>

      {/* Bear Case */}
      <div>
        <div className="flex items-center gap-2 mb-3">
          <div className="w-2 h-2 rounded-full bg-accent-red" />
          <h3 className="text-sm font-medium text-text-primary">약세 논거 (Bear Case)</h3>
        </div>
        <div className="space-y-2">
          {bearCases.map((p) => (
            <CaseCard key={p.point_id} point={p} type="bear" />
          ))}
        </div>
      </div>
    </div>
  );
}
