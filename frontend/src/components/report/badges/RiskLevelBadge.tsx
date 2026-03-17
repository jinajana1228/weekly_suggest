import type { RiskLevel } from "@/types/enums";
import { RISK_LABELS, RISK_COLORS } from "@/lib/constants";

interface RiskLevelBadgeProps {
  level: RiskLevel;
  size?: "sm" | "md";
}

export function RiskLevelBadge({ level, size = "sm" }: RiskLevelBadgeProps) {
  const colorClass = RISK_COLORS[level];
  const label = RISK_LABELS[level];
  const sizeClass = size === "md" ? "px-3 py-1 text-sm" : "px-2 py-0.5 text-xs";

  return (
    <span className={`inline-flex items-center gap-1 rounded border font-medium ${sizeClass} ${colorClass}`}>
      <span className="w-1.5 h-1.5 rounded-full bg-current opacity-70" />
      {label}
    </span>
  );
}
