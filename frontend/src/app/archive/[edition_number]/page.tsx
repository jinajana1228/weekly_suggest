import { notFound } from "next/navigation";
import { apiClient } from "@/lib/api-client";
import { StockCard } from "@/components/report/StockCard";
import { DisclaimerBanner } from "@/components/layout/DisclaimerBanner";
import { formatDate } from "@/lib/formatters";
import Link from "next/link";

interface PageProps {
  params: { edition_number: string };
}

export default async function ArchiveEditionPage({ params }: PageProps) {
  const editionNumber = parseInt(params.edition_number);

  if (isNaN(editionNumber)) notFound();

  let edition = null;
  try {
    edition = await apiClient.getArchiveEdition(editionNumber);
  } catch (e) {
    notFound();
  }

  if (!edition) notFound();

  const headerDisclaimer = edition.disclaimer_blocks?.find((b) => b.position === "HEADER");

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6 space-y-3">
        <Link href="/archive" className="inline-flex items-center gap-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors">
          ← 발행 이력
        </Link>
        {headerDisclaimer && <DisclaimerBanner content={headerDisclaimer.content} />}
      </div>

      <div className="mb-6">
        <div className="flex items-start justify-between gap-4 mb-2">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-accent-gold border border-yellow-800 bg-yellow-950 rounded px-2 py-0.5">
                VOL.{edition.edition_number}
              </span>
              <span className={`text-xs border rounded px-2 py-0.5 ${
                edition.status === "ARCHIVED"
                  ? "text-text-muted border-border-default"
                  : "text-accent-green border-green-900 bg-green-950"
              }`}>
                {edition.status === "ARCHIVED" ? "아카이브" : "발행됨"}
              </span>
            </div>
            <h1 className="text-xl font-semibold text-text-primary">
              저평가 후보 종목 리포트
            </h1>
            <p className="text-xs text-text-muted mt-1">
              발행: {formatDate(edition.published_at, "long")} · 기준일: {formatDate(edition.data_as_of)}
            </p>
          </div>
        </div>

        {edition.market_context_note && (
          <div className="bg-bg-surface border border-border-default rounded-lg px-4 py-3 mt-3">
            <p className="text-xs text-text-secondary leading-relaxed">
              <span className="text-text-muted mr-1.5">시황 맥락</span>
              {edition.market_context_note}
            </p>
          </div>
        )}
      </div>

      <div className="space-y-3">
        {edition.stocks.map((stock) => (
          <StockCard
            key={stock.report_item_id}
            stock={stock}
            reportId={edition.report_id}
            dataAsOf={edition.data_as_of}
          />
        ))}
      </div>

      <div className="mt-8 pt-6 border-t border-border-default text-center">
        <Link href="/archive" className="text-xs text-text-muted hover:text-text-secondary transition-colors">
          ← 발행 이력으로 돌아가기
        </Link>
      </div>
    </div>
  );
}
