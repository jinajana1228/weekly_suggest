import Link from "next/link";

interface DisclaimerBannerProps {
  content?: string;
}

export function DisclaimerBanner({ content }: DisclaimerBannerProps) {
  const defaultContent =
    "본 리포트는 투자 권유가 아닙니다. 제시된 분석은 공개된 데이터에 기반한 정보 제공 목적이며, 투자 손익을 보장하지 않습니다. 모든 투자 결정은 투자자 본인의 판단과 책임 하에 이루어져야 합니다.";

  return (
    <div className="bg-bg-overlay border border-border-default rounded-lg px-4 py-3 flex items-start gap-3">
      <div className="shrink-0 w-4 h-4 mt-0.5 rounded-full border border-text-muted flex items-center justify-center">
        <span className="text-text-muted text-[9px] font-bold">!</span>
      </div>
      <p className="text-xs text-text-muted leading-relaxed flex-1">
        {content || defaultContent}{" "}
        <Link href="/disclaimer" className="text-text-secondary hover:text-text-primary underline underline-offset-2 transition-colors">
          면책 고지 전문 보기
        </Link>
      </p>
    </div>
  );
}
