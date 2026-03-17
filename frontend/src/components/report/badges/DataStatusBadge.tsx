import type { DataStatus } from "@/types/enums";

interface DataStatusBadgeProps {
  status: DataStatus;
  className?: string;
}

const STATUS_CONFIG: Record<DataStatus, { label: string; className: string }> = {
  CONFIRMED: { label: "확인됨", className: "text-text-muted" },
  UNVERIFIED: { label: "미검증", className: "text-yellow-600" },
  UNAVAILABLE: { label: "데이터 없음", className: "text-text-muted italic" },
  NOT_APPLICABLE: { label: "해당 없음", className: "text-text-muted italic" },
  STALE: { label: "기간 초과", className: "text-yellow-700" },
};

export function DataStatusBadge({ status, className = "" }: DataStatusBadgeProps) {
  const config = STATUS_CONFIG[status];
  return (
    <span className={`text-xs ${config.className} ${className}`}>
      {config.label}
    </span>
  );
}

interface DataValueDisplayProps {
  value: { value: number | null; status: DataStatus } | null | undefined;
  formatter: (v: number | null) => string;
  className?: string;
}

export function DataValueDisplay({ value, formatter, className = "" }: DataValueDisplayProps) {
  if (!value) return <span className="text-text-muted text-sm font-mono">—</span>;

  if (value.status === "UNAVAILABLE" || value.status === "NOT_APPLICABLE") {
    return (
      <span className="text-text-muted text-sm italic">
        {value.status === "NOT_APPLICABLE" ? "해당 없음" : "—"}
      </span>
    );
  }

  if (value.value === null) {
    return <span className="text-text-muted text-sm font-mono">—</span>;
  }

  return (
    <span className={`font-mono ${className}`}>
      {formatter(value.value)}
      {value.status === "STALE" && (
        <span className="ml-1 text-yellow-700 text-[10px]">†</span>
      )}
      {value.status === "UNVERIFIED" && (
        <span className="ml-1 text-yellow-600 text-[10px]">*</span>
      )}
    </span>
  );
}
