import Link from "next/link";

export function Footer() {
  return (
    <footer className="border-t border-border-default mt-16">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
          <div>
            <p className="text-xs text-text-muted leading-relaxed max-w-xl">
              본 서비스는 투자 권유를 목적으로 하지 않습니다. 제공되는 모든 분석과 정보는
              투자 판단의 참고 자료일 뿐이며, 투자 손익에 대한 책임은 투자자 본인에게 있습니다.
            </p>
          </div>
          <div className="flex items-center gap-4 shrink-0">
            <Link href="/disclaimer" className="text-xs text-text-muted hover:text-text-secondary transition-colors">
              면책 고지 전문
            </Link>
            <span className="text-border-default">|</span>
            <span className="text-xs text-text-muted">© 2025 Weekly Suggest</span>
          </div>
        </div>
      </div>
    </footer>
  );
}
