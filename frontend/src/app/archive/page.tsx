import { apiClient } from "@/lib/api-client";
import type { ArchiveEntry } from "@/types/schema";
import Link from "next/link";
import { formatDate } from "@/lib/formatters";
import { RiskLevelBadge } from "@/components/report/badges/RiskLevelBadge";
import { CatalystBadgeGroup } from "@/components/report/badges/CatalystBadge";
import { SignalBadge } from "@/components/report/badges/SignalBadge";

export default async function ArchivePage() {
  let editions: ArchiveEntry[] = [];

  try {
    editions = await apiClient.getArchive();
  } catch {
    // fallback to empty
  }

  const latestEdition = editions[0];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <h1 className="text-xl font-semibold text-text-primary tracking-tight">발행 이력</h1>
        <p className="text-sm text-text-muted mt-1">
          발행된 모든 에디션을 시간 순으로 확인합니다. 최신 에디션은{" "}
          <Link href="/" className="underline underline-offset-2 hover:text-text-secondary transition-colors">
            메인 페이지
          </Link>
          에서 볼 수 있습니다.
        </p>
      </div>

      {editions.length === 0 ? (
        <div className="text-center py-16">
          <p className="text-text-muted text-sm">발행 이력 없음</p>
        </div>
      ) : (
        <div className="space-y-4">
          {editions.map((edition, idx) => {
            const isLatest = idx === 0 && edition.status === "PUBLISHED";
            const issueTypeLabel =
              edition.issue_type === "EARNINGS_TRIGGERED"
                ? "실적 트리거"
                : edition.issue_type === "SPECIAL_EVENT"
                ? "특별 발행"
                : "격주 정기";
            const issueTypeBadgeClass =
              edition.issue_type === "EARNINGS_TRIGGERED"
                ? "text-amber-400 border-amber-800 bg-amber-950/40"
                : edition.issue_type === "SPECIAL_EVENT"
                ? "text-sky-400 border-sky-800 bg-sky-950/40"
                : "text-text-muted border-border-default bg-bg-surface";

            return (
              <div
                key={edition.report_id}
                className={`bg-bg-surface border rounded-lg overflow-hidden transition-colors ${
                  isLatest
                    ? "border-emerald-800/60 hover:border-emerald-700"
                    : "border-border-default hover:border-zinc-600"
                }`}
              >
                {/* 에디션 헤더 */}
                <div className="px-5 py-4 border-b border-border-default flex items-start justify-between gap-4">
                  <div>
                    <div className="flex items-center gap-2 mb-1.5 flex-wrap">
                      <span className="font-mono text-xs text-accent-gold border border-yellow-800 bg-yellow-950 rounded px-2 py-0.5">
                        VOL.{edition.edition_number}
                      </span>
                      <span className={`text-[10px] border rounded px-2 py-0.5 ${issueTypeBadgeClass}`}>
                        {issueTypeLabel}
                      </span>
                      {isLatest ? (
                        <span className="text-[10px] text-emerald-400 border border-emerald-800 bg-emerald-950/40 rounded px-2 py-0.5">
                          최신 발행
                        </span>
                      ) : (
                        <span className="text-[10px] text-text-muted border border-border-default rounded px-2 py-0.5">
                          {edition.status === "ARCHIVED" ? "아카이브" : "발행됨"}
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-text-muted">
                      발행: {formatDate(edition.published_at, "long")}
                      {" · "}
                      기준일: {formatDate(edition.data_as_of)}
                      {" · "}
                      <span className="font-mono">{edition.report_id}</span>
                    </p>
                  </div>
                  <Link
                    href={`/archive/${edition.edition_number}`}
                    className="text-xs text-text-muted hover:text-text-primary border border-border-default hover:border-zinc-600 rounded px-3 py-1.5 transition-colors shrink-0"
                  >
                    상세 보기
                  </Link>
                </div>

                {/* 시황 노트 */}
                {edition.market_context_note && (
                  <div className="px-5 py-3 border-b border-border-default">
                    <p className="text-xs text-text-muted leading-relaxed line-clamp-2">
                      {edition.market_context_note}
                    </p>
                  </div>
                )}

                {/* 종목 요약 */}
                <div className="px-5 py-3">
                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
                    {edition.stocks?.slice(0, 6).map((stock) => (
                      <div
                        key={stock.report_item_id}
                        className="flex items-center justify-between gap-2 bg-bg-overlay rounded px-2.5 py-2"
                      >
                        <div className="min-w-0">
                          <div className="flex items-center gap-1.5">
                            <span className="font-mono text-xs font-bold text-text-primary">
                              {stock.ticker}
                            </span>
                            <span className="text-[10px] text-text-muted truncate">
                              {stock.sector.split(" ")[0]}
                            </span>
                          </div>
                        </div>
                        <div className="flex items-center gap-1 shrink-0">
                          <CatalystBadgeGroup badges={stock.catalyst_badges} />
                          <RiskLevelBadge level={stock.risk_level_overall} />
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 발행 정책 안내 */}
      <div className="mt-8 pt-6 border-t border-border-default">
        <p className="text-xs text-text-muted leading-relaxed">
          <span className="text-text-secondary font-medium">발행 정책</span>
          {" — "}
          격주 월요일 오전 8시 정기 발행 · 주요 어닝 시즌/이벤트 발생 시 임시 발행.
          모든 에디션은 스크리닝 → 편집자 검토 → 발행 게이트를 통과합니다.
        </p>
      </div>
    </div>
  );
}
