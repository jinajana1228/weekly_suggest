import type { CatalystStatus } from "@/types/enums";
import { CATALYST_LABELS, CATALYST_COLORS } from "@/lib/constants";

interface CatalystBadgeProps {
  catalystId: "A" | "B" | "C";
  status: CatalystStatus;
  showLabel?: boolean;
}

export function CatalystBadge({ catalystId, status, showLabel = false }: CatalystBadgeProps) {
  const colorClass = CATALYST_COLORS[status];
  const label = CATALYST_LABELS[status];

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-medium ${colorClass}`}
      title={`Catalyst ${catalystId}: ${label}`}
    >
      <span className="font-mono font-bold">{catalystId}</span>
      {showLabel && <span className="text-[10px]">{label}</span>}
    </span>
  );
}

interface CatalystBadgeGroupProps {
  badges: Array<{ catalyst_id: "A" | "B" | "C"; status: CatalystStatus }>;
  showLabels?: boolean;
}

export function CatalystBadgeGroup({ badges, showLabels = false }: CatalystBadgeGroupProps) {
  return (
    <div className="flex items-center gap-1">
      {badges.map((badge) => (
        <CatalystBadge
          key={badge.catalyst_id}
          catalystId={badge.catalyst_id}
          status={badge.status}
          showLabel={showLabels}
        />
      ))}
    </div>
  );
}
