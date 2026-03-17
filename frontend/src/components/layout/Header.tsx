import Link from "next/link";

export function Header() {
  return (
    <header className="border-b border-border-default bg-bg-base sticky top-0 z-50">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between">
        {/* 로고 */}
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-6 h-6 rounded border border-accent-gold/40 flex items-center justify-center">
            <span className="text-accent-gold text-xs font-bold">W</span>
          </div>
          <span className="font-semibold text-sm tracking-wide text-text-primary group-hover:text-accent-gold transition-colors">
            WEEKLY SUGGEST
          </span>
        </Link>

        {/* 네비게이션 */}
        <nav className="flex items-center gap-6">
          <Link
            href="/"
            className="text-xs text-text-secondary hover:text-text-primary transition-colors"
          >
            리포트
          </Link>
          <Link
            href="/archive"
            className="text-xs text-text-secondary hover:text-text-primary transition-colors"
          >
            아카이브
          </Link>
          <Link
            href="/admin"
            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            관리
          </Link>
          <Link
            href="/disclaimer"
            className="text-xs text-text-muted hover:text-text-secondary transition-colors"
          >
            면책
          </Link>
        </nav>
      </div>
    </header>
  );
}
