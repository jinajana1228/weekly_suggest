import type { AnalystStyleSummary, NarrativeBlock } from "@/types/schema";

interface NarrativeSectionProps {
  summary: AnalystStyleSummary;
}

const NARRATIVE_CONFIG = [
  {
    key: "why_discounted" as const,
    title: "왜 할인받고 있는가",
    subtitle: "시장 할인 원인 분석",
    icon: "↓",
    iconColor: "text-rose-400",
    borderColor: "border-rose-900/50",
  },
  {
    key: "why_worth_revisiting" as const,
    title: "왜 지금 다시 볼 만한가",
    subtitle: "리레이팅 근거",
    icon: "↑",
    iconColor: "text-sky-400",
    borderColor: "border-sky-900/50",
  },
  {
    key: "key_risks_narrative" as const,
    title: "핵심 리스크 종합",
    subtitle: "주요 위험 요인 요약",
    icon: "!",
    iconColor: "text-amber-400",
    borderColor: "border-amber-900/50",
  },
  {
    key: "investment_context" as const,
    title: "투자 맥락 요약",
    subtitle: "종합 시각",
    icon: "◎",
    iconColor: "text-text-muted",
    borderColor: "border-border-default",
  },
];

function NarrativeBlockCard({
  block,
  title,
  subtitle,
  icon,
  iconColor,
  borderColor,
}: {
  block: NarrativeBlock;
  title: string;
  subtitle: string;
  icon: string;
  iconColor: string;
  borderColor: string;
}) {
  if (block.status === "FLAGGED_FOR_REVISION") {
    return (
      <div className="bg-bg-surface border border-yellow-900/60 rounded-lg p-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-[10px] text-yellow-600 border border-yellow-900 rounded px-1.5 py-0.5">검토 중</span>
          <span className="text-xs text-text-muted">{title}</span>
        </div>
        <p className="text-xs text-text-muted">이 서술은 검토 중입니다.</p>
      </div>
    );
  }

  if (block.status === "PLACEHOLDER" || !block.content || block.content.includes("준비 중")) {
    return (
      <div className="bg-bg-surface border border-border-default rounded-lg p-4 opacity-50">
        <div className="flex items-center gap-2 mb-2">
          <span className={`font-mono text-sm ${iconColor} opacity-40`}>{icon}</span>
          <div>
            <span className="text-xs text-text-muted">{title}</span>
          </div>
        </div>
        <div className="h-3 bg-bg-overlay rounded w-3/4 mb-2" />
        <div className="h-3 bg-bg-overlay rounded w-full mb-2" />
        <div className="h-3 bg-bg-overlay rounded w-2/3" />
      </div>
    );
  }

  return (
    <div className={`bg-bg-surface border ${borderColor} rounded-lg p-4`}>
      <div className="flex items-start gap-3 mb-3">
        <span className={`font-mono font-bold text-base ${iconColor} mt-0.5 shrink-0`}>{icon}</span>
        <div>
          <h4 className="text-sm font-semibold text-text-primary leading-tight">{title}</h4>
          <p className="text-[10px] text-text-muted mt-0.5">{subtitle}</p>
        </div>
      </div>
      <p className="text-sm text-text-secondary leading-relaxed pl-6">{block.content}</p>
    </div>
  );
}

export function NarrativeSection({ summary }: NarrativeSectionProps) {
  const isAllPlaceholder = NARRATIVE_CONFIG.every(
    (c) =>
      summary[c.key].status === "PLACEHOLDER" ||
      !summary[c.key].content ||
      summary[c.key].content.includes("준비 중") ||
      summary[c.key].content.includes("비활성화")
  );
  const isGenerated = summary.model_id && summary.model_id !== "placeholder";

  return (
    <div className="space-y-3">
      {/* 헤더 메타 */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isGenerated ? (
            <>
              <span className="text-[10px] text-text-muted border border-border-default rounded px-1.5 py-0.5">
                {summary.model_id}
              </span>
              {summary.reviewer_approved && (
                <span className="text-[10px] text-emerald-400 border border-emerald-900 bg-emerald-950/40 rounded px-1.5 py-0.5">
                  검토 완료
                </span>
              )}
            </>
          ) : (
            <span className="text-[10px] text-text-muted border border-dashed border-border-default rounded px-1.5 py-0.5">
              서술 미생성
            </span>
          )}
        </div>
        <p className="text-[10px] text-text-muted">구조화 데이터 기반 AI 보조 분석</p>
      </div>

      {/* PLACEHOLDER 전체 상태 안내 */}
      {isAllPlaceholder && (
        <div className="bg-bg-surface border border-dashed border-zinc-700 rounded-lg p-4 text-center">
          <p className="text-xs text-text-muted mb-1">애널리스트 서술이 아직 생성되지 않았습니다.</p>
          <p className="text-[10px] text-text-muted opacity-70">
            ANTHROPIC_API_KEY 설정 후{" "}
            <code className="font-mono bg-bg-overlay px-1 rounded">
              python scripts/generate_narratives.py
            </code>{" "}
            를 실행하세요.
          </p>
        </div>
      )}

      {/* 4개 블록 — 전체 PLACEHOLDER이면 스켈레톤 숨김 */}
      {!isAllPlaceholder && NARRATIVE_CONFIG.map((config) => (
        <NarrativeBlockCard
          key={config.key}
          block={summary[config.key]}
          title={config.title}
          subtitle={config.subtitle}
          icon={config.icon}
          iconColor={config.iconColor}
          borderColor={config.borderColor}
        />
      ))}
    </div>
  );
}
