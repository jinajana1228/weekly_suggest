import { notFound } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { PriceChart } from "@/components/chart/PriceChart";
import { PriceContextSection } from "@/components/report/sections/PriceContextSection";
import { ValuationSection } from "@/components/report/sections/ValuationSection";
import { CatalystSection } from "@/components/report/sections/CatalystSection";
import { BullBearSection } from "@/components/report/sections/BullBearSection";
import { RiskSection } from "@/components/report/sections/RiskSection";
import { NarrativeSection } from "@/components/report/sections/NarrativeSection";
import { InterestRangeSection } from "@/components/report/sections/InterestRangeSection";
import { FinancialsTable } from "@/components/report/sections/FinancialsTable";
import { DataQualitySection } from "@/components/report/sections/DataQualitySection";
import { RiskLevelBadge } from "@/components/report/badges/RiskLevelBadge";
import { SignalBadge } from "@/components/report/badges/SignalBadge";
import { CatalystBadgeGroup } from "@/components/report/badges/CatalystBadge";
import { DisclaimerBanner } from "@/components/layout/DisclaimerBanner";
import { formatPrice, formatDate } from "@/lib/formatters";
import Link from "next/link";

interface PageProps {
  params: { report_item_id: string };
  searchParams: { report_id?: string };
}

// report_item_id에서 ticker와 report_id 추출
// 형식: ri_20250317_002_MFGI
function parseReportItemId(id: string): { ticker: string; reportId: string } {
  const parts = id.split("_");
  const ticker = parts[parts.length - 1];
  // re_YYYYMMDD_NNN 형식으로 재구성
  const reportId = `re_${parts[1]}_${parts[2]}`;
  return { ticker, reportId };
}

export default async function StockReportPage({ params, searchParams }: PageProps) {
  const { report_item_id } = params;
  const { ticker, reportId } = parseReportItemId(report_item_id);
  const finalReportId = searchParams.report_id || reportId;

  let report = null;
  let chartData = null;

  try {
    [report, chartData] = await Promise.all([
      apiClient.getStockReport(finalReportId, ticker),
      apiClient.getChartData(ticker, 365),
    ]);
  } catch (e) {
    notFound();
  }

  if (!report) notFound();

  const headerDisclaimer = report.disclaimer_blocks.find((b) => b.position === "HEADER");
  const footerDisclaimer = report.disclaimer_blocks.find((b) => b.position === "FOOTER");

  const SECTIONS = [
    { id: "chart", label: "차트" },
    { id: "price", label: "가격" },
    { id: "valuation", label: "밸류에이션" },
    { id: "catalyst", label: "촉매" },
    { id: "bull-bear", label: "강세/약세" },
    { id: "risk", label: "리스크" },
    { id: "narrative", label: "분석" },
    { id: "financials", label: "재무" },
  ];

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* 뒤로가기 + 면책 배너 */}
      <div className="mb-6 space-y-3">
        <div className="flex items-center gap-3">
          <Link
            href="/"
            className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            ← 최신 리포트
          </Link>
          <span className="text-border-default text-xs">|</span>
          <span className="text-xs font-mono text-text-muted">{finalReportId}</span>
        </div>
        {headerDisclaimer && <DisclaimerBanner content={headerDisclaimer.content} />}
      </div>

      {/* 종목 헤더 */}
      <div className="mb-6">
        <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 flex-wrap mb-1">
              <h1 className="font-mono text-3xl font-bold text-text-primary tracking-wide">
                {report.ticker}
              </h1>
              <span className="text-xs border border-border-default rounded px-2 py-0.5 text-text-muted">
                {report.exchange}
              </span>
              <SignalBadge
                signal={report.undervaluation_judgment.combined_signal}
                discountPct={report.valuation.valuation_discount_vs_sector.discount_pct ?? undefined}
                size="md"
              />
              <RiskLevelBadge level={(() => {
                const order: Record<string, number> = { HIGH: 3, MEDIUM: 2, LOW: 1, UNASSESSED: 0 };
                return (report.short_term_risks ?? []).concat(report.structural_risks ?? []).reduce((max, r) =>
                  order[r.severity] > order[max] ? r.severity : max, "LOW" as string
                ) as import("@/types/enums").RiskLevel;
              })()} size="md" />
            </div>
            <h2 className="text-lg font-medium text-text-secondary">
              {report.company_name}
            </h2>
            <p className="text-sm text-text-muted mt-0.5">
              {report.sector} · {report.industry}
            </p>
          </div>

          <div className="text-right shrink-0">
            <div className="font-mono text-2xl font-bold text-text-primary">
              {formatPrice(report.current_price.value)}
            </div>
            <div className="text-xs text-text-muted mt-1">
              기준: {formatDate(report.current_price.as_of)}
            </div>
            <div className="mt-1">
              <CatalystBadgeGroup badges={report.catalyst_assessment.catalyst_a ? [
                { catalyst_id: "A", status: report.catalyst_assessment.catalyst_a.status },
                { catalyst_id: "B", status: report.catalyst_assessment.catalyst_b.status },
                { catalyst_id: "C", status: report.catalyst_assessment.catalyst_c.status },
              ] : []} />
            </div>
          </div>
        </div>

        {/* 한 줄 사업 설명 */}
        <div className="mt-3 bg-bg-surface border border-border-default rounded-lg px-4 py-3">
          <p className="text-xs text-text-secondary leading-relaxed">
            {report.stock_info.short_description}
          </p>
        </div>
      </div>

      {/* 차트 + 관심가격구간 */}
      <div id="chart" className="mb-6 bg-bg-surface border border-border-default rounded-lg p-4">
        {chartData && chartData.price_series.length > 0 ? (
          <PriceChart chartData={chartData} height={280} />
        ) : (
          <div className="h-40 flex items-center justify-center">
            <p className="text-text-muted text-sm">차트 데이터 없음</p>
          </div>
        )}
      </div>

      {/* 섹션 네비게이션 */}
      <div className="sticky top-[56px] z-40 -mx-4 sm:-mx-6 px-4 sm:px-6 py-2 bg-bg-base/90 backdrop-blur border-b border-border-default mb-6">
        <div className="flex gap-1 overflow-x-auto scrollbar-hide">
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              className="shrink-0 px-3 py-1.5 text-xs text-text-muted hover:text-text-primary border border-border-default rounded hover:border-zinc-600 transition-all bg-bg-surface/80"
            >
              {s.label}
            </a>
          ))}
        </div>
      </div>

      {/* 본문 섹션들 */}
      <div className="space-y-10">
        {/* 가격 맥락 */}
        <section id="price">
          <SectionTitle title="가격 맥락" />
          <PriceContextSection report={report} />
        </section>

        {/* 관심 가격 구간 */}
        <section>
          <InterestRangeSection
            range={report.interest_price_range}
            currentPrice={report.current_price.value}
          />
        </section>

        {/* 밸류에이션 */}
        <section id="valuation">
          <SectionTitle title="밸류에이션 분석" />
          <ValuationSection report={report} />
        </section>

        {/* 촉매 */}
        <section id="catalyst">
          <SectionTitle title="리레이팅 촉매 평가" />
          <CatalystSection report={report} />
        </section>

        {/* 강세/약세 */}
        <section id="bull-bear">
          <SectionTitle title="강세 / 약세 논거" />
          <BullBearSection
            bullCases={report.bull_case_points}
            bearCases={report.bear_case_points}
          />
        </section>

        {/* 리스크 */}
        <section id="risk">
          <SectionTitle title="리스크 분석" />
          <RiskSection
            structuralRisks={report.structural_risks}
            shortTermRisks={report.short_term_risks}
          />
        </section>

        {/* LLM 분석 서술 */}
        <section id="narrative">
          <SectionTitle title="구조적 분석 서술" badge="AI 보조 · 수치 기반" />
          <NarrativeSection summary={report.analyst_style_summary} />
        </section>

        {/* 재무 지표 */}
        <section id="financials">
          <SectionTitle title="핵심 재무 지표" />
          <FinancialsTable report={report} />
        </section>

        {/* 데이터 품질 + 출처 */}
        <section>
          <SectionTitle title="데이터 품질 및 출처" />
          <DataQualitySection report={report} />
        </section>
      </div>

      {/* 푸터 면책 */}
      {footerDisclaimer && (
        <div className="mt-10 pt-8 border-t border-border-default">
          <div className="bg-bg-surface border border-border-default rounded-lg p-4">
            <h3 className="text-xs font-medium text-text-muted mb-2">면책 고지</h3>
            <p className="text-xs text-text-muted leading-relaxed">{footerDisclaimer.content}</p>
          </div>
        </div>
      )}

      <div className="mt-6 text-center">
        <Link href="/" className="text-xs text-text-muted hover:text-text-secondary transition-colors">
          ← 리포트 목록으로 돌아가기
        </Link>
      </div>
    </div>
  );
}

function SectionTitle({ title, badge }: { title: string; badge?: string }) {
  return (
    <div className="flex items-center gap-2 mb-3">
      <div className="w-0.5 h-4 bg-accent-gold rounded-full opacity-60" />
      <h2 className="text-base font-semibold text-text-primary">{title}</h2>
      {badge && (
        <span className="text-[10px] text-text-muted border border-border-default rounded px-1.5 py-0.5">
          {badge}
        </span>
      )}
    </div>
  );
}
