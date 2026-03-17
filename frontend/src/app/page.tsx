import { apiClient } from "@/lib/api-client";
import { StockCard } from "@/components/report/StockCard";
import { DisclaimerBanner } from "@/components/layout/DisclaimerBanner";
import { formatDate } from "@/lib/formatters";

export default async function HomePage() {
  let edition = null;
  let error = null;

  try {
    edition = await apiClient.getLatestReport();
  } catch {
    error = "리포트를 불러오는 중 오류가 발생했습니다.";
  }

  if (error || !edition) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-text-muted text-sm">{error || "발행된 리포트가 없습니다."}</p>
        <p className="text-xs text-text-muted mt-2">백엔드 서버가 실행 중인지 확인해주세요.</p>
      </div>
    );
  }

  const headerDisclaimer = edition.disclaimer_blocks?.find((b) => b.position === "HEADER");

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
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* 에디션 메타 헤더 */}
      <div className="mb-6">
        <div className="flex items-start justify-between gap-4 mb-3">
          <div>
            {/* 배지 행 */}
            <div className="flex items-center gap-2 mb-2 flex-wrap">
              <span className="text-[10px] font-mono text-accent-gold border border-yellow-800 bg-yellow-950/60 rounded px-2 py-0.5">
                VOL.{edition.edition_number}
              </span>
              <span className={`text-[10px] border rounded px-2 py-0.5 ${issueTypeBadgeClass}`}>
                {issueTypeLabel}
              </span>
              <span className="text-[10px] text-emerald-400 border border-emerald-800 bg-emerald-950/40 rounded px-2 py-0.5">
                PUBLISHED
              </span>
            </div>

            <h1 className="text-xl font-semibold text-text-primary tracking-tight">
              저평가 후보 종목 리포트
            </h1>
            <p className="text-sm text-text-muted mt-0.5">
              {edition.stocks.length}개 종목 · 데이터 기준일{" "}
              <span className="font-mono text-text-secondary">{formatDate(edition.data_as_of)}</span>
            </p>
          </div>

          <div className="shrink-0 text-right">
            <div className="text-[10px] text-text-muted mb-0.5">발행일</div>
            <div className="text-sm font-mono text-text-secondary">
              {formatDate(edition.published_at ?? edition.data_as_of, "long")}
            </div>
          </div>
        </div>

        {/* 시황 노트 */}
        {edition.market_context_note && (
          <div className="bg-bg-surface border border-border-default rounded-lg px-4 py-3 mb-3">
            <p className="text-xs text-text-secondary leading-relaxed">
              <span className="text-text-muted mr-2 font-medium">시황 맥락</span>
              {edition.market_context_note}
            </p>
          </div>
        )}

        {/* 서비스 안내 배너 */}
        <div className="flex items-center gap-3 bg-bg-surface/50 border border-dashed border-zinc-700 rounded-lg px-4 py-2.5">
          <div className="w-1 h-8 bg-accent-gold/30 rounded-full shrink-0" />
          <div>
            <p className="text-[11px] text-text-secondary leading-relaxed">
              이 리포트는 <span className="text-text-primary font-medium">격주 월요일 오전 8시</span>에 발행됩니다.
              스크리닝 → 편집자 검토 → 발행 게이트를 통과한 종목만 수록됩니다.
            </p>
            <p className="text-[10px] text-text-muted mt-0.5">
              페이지 방문 시 재계산하지 않음 · 이전 리포트는{" "}
              <a href="/archive" className="underline underline-offset-2 hover:text-text-secondary transition-colors">
                아카이브
              </a>
              에서 확인
            </p>
          </div>
        </div>
      </div>

      {/* 면책 배너 */}
      {headerDisclaimer && (
        <div className="mb-6">
          <DisclaimerBanner content={headerDisclaimer.content} />
        </div>
      )}

      {/* 종목 카드 리스트 */}
      <div className="space-y-2.5">
        {edition.stocks.map((stock, idx) => (
          <div key={stock.report_item_id} className="relative pl-7 sm:pl-8">
            <div className="absolute left-0 top-1/2 -translate-y-1/2">
              <span className="text-[10px] font-mono text-text-muted opacity-40">{idx + 1}</span>
            </div>
            <StockCard stock={stock} reportId={edition.report_id} dataAsOf={edition.data_as_of} />
          </div>
        ))}
      </div>

      {/* 하단 */}
      <div className="mt-10 pt-6 border-t border-border-default flex items-center justify-between">
        <p className="text-xs text-text-muted">
          발행: {formatDate(edition.published_at ?? edition.data_as_of, "long")}
          {" · "}report ID:{" "}
          <span className="font-mono">{edition.report_id}</span>
        </p>
        <a href="/archive" className="text-xs text-text-muted hover:text-text-secondary transition-colors">
          이전 리포트 →
        </a>
      </div>
    </div>
  );
}
