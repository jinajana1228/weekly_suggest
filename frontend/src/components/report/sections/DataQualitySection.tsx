import type { StockReport } from "@/types/schema";
import { formatDate } from "@/lib/formatters";

interface DataQualitySectionProps {
  report: StockReport;
}

export function DataQualitySection({ report }: DataQualitySectionProps) {
  const { data_quality_flags, data_sources } = report;
  const warnings = data_quality_flags.filter((f) => f.severity === "WARNING");
  const infos = data_quality_flags.filter((f) => f.severity === "INFO");

  return (
    <div className="space-y-3">
      {/* 데이터 품질 플래그 */}
      {data_quality_flags.length > 0 && (
        <div className="bg-bg-surface border border-border-default rounded-lg p-4">
          <h3 className="text-sm font-medium text-text-primary mb-3">데이터 품질 공지</h3>
          <div className="space-y-2">
            {warnings.map((flag) => (
              <div key={flag.flag_id} className="flex items-start gap-2 bg-yellow-950/30 border border-yellow-900/50 rounded p-2.5">
                <span className="text-yellow-500 text-xs shrink-0">⚠</span>
                <div>
                  <p className="text-xs text-yellow-400 font-medium mb-0.5">{flag.field_path}</p>
                  <p className="text-xs text-yellow-600/80">{flag.message}</p>
                </div>
              </div>
            ))}
            {infos.map((flag) => (
              <div key={flag.flag_id} className="flex items-start gap-2 bg-bg-overlay border border-border-default rounded p-2.5">
                <span className="text-text-muted text-xs shrink-0">ⓘ</span>
                <div>
                  <p className="text-xs text-text-secondary font-medium mb-0.5">{flag.field_path}</p>
                  <p className="text-xs text-text-muted">{flag.message}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 데이터 출처 */}
      <div className="bg-bg-surface border border-border-default rounded-lg p-4">
        <h3 className="text-sm font-medium text-text-primary mb-3">데이터 출처 및 기준일</h3>
        <div className="space-y-1.5">
          {data_sources.map((src) => (
            <div key={src.source_id} className="flex items-center justify-between text-xs">
              <span className="text-text-secondary">{src.provider_name} ({src.data_category})</span>
              <span className="text-text-muted font-mono">
                {new Date(src.as_of).toLocaleDateString("ko-KR")}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
