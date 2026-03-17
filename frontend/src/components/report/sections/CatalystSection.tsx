import type { StockReport } from "@/types/schema";
import { CatalystBadge } from "../badges/CatalystBadge";
import { CATALYST_LABELS } from "@/lib/constants";

interface CatalystSectionProps {
  report: StockReport;
}

export function CatalystSection({ report }: CatalystSectionProps) {
  const { catalyst_assessment } = report;
  const catalysts = [
    { key: "catalyst_a", data: catalyst_assessment.catalyst_a, label: "어닝 촉매" },
    { key: "catalyst_b", data: catalyst_assessment.catalyst_b, label: "컨센서스 갭" },
    { key: "catalyst_c", data: catalyst_assessment.catalyst_c, label: "과매도 해소" },
  ];

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-xs text-text-muted">
          충족 조건: <span className="text-text-primary font-medium font-mono">{catalyst_assessment.met_count}/3</span>
        </div>
        <span className="text-xs text-accent-blue">{catalyst_assessment.composite_label}</span>
      </div>

      {catalysts.map(({ key, data, label }) => (
        <div
          key={key}
          className="bg-bg-surface border border-border-default rounded-lg p-4"
        >
          <div className="flex items-start gap-3">
            <div className="shrink-0 mt-0.5">
              <CatalystBadge catalystId={data.catalyst_id} status={data.status} showLabel />
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-xs font-medium text-text-primary">
                  Catalyst {data.catalyst_id}: {label}
                </span>
              </div>
              <p className="text-xs text-text-muted mb-2">{data.definition_summary}</p>
              {data.evidence ? (
                <p className="text-xs text-text-secondary leading-relaxed bg-bg-overlay rounded px-2.5 py-2">
                  {data.evidence}
                </p>
              ) : (
                <p className="text-xs text-text-muted italic bg-bg-overlay rounded px-2.5 py-2">
                  {data.status === "UNVERIFIABLE" ? "데이터 소스 미확인으로 판단 불가" : "근거 없음"}
                </p>
              )}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}
