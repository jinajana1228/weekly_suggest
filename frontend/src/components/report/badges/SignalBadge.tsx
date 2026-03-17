import type { UndervaluationSignal } from "@/types/enums";
import { SIGNAL_LABELS, SIGNAL_COLORS } from "@/lib/constants";

interface SignalBadgeProps {
  signal: UndervaluationSignal;
  discountPct?: number;
  size?: "sm" | "md";
}

export function SignalBadge({ signal, discountPct, size = "sm" }: SignalBadgeProps) {
  const colorClass = SIGNAL_COLORS[signal];
  const label = SIGNAL_LABELS[signal];
  const sizeClass = size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";

  return (
    <span className={`inline-flex items-center gap-1.5 rounded border font-medium ${sizeClass} ${colorClass}`}>
      {discountPct !== undefined && (
        <span className="font-mono font-bold">{discountPct.toFixed(1)}%↓</span>
      )}
      <span>{label}</span>
    </span>
  );
}
