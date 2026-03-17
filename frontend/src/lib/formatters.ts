/**
 * 숫자/날짜/텍스트 포맷 유틸리티
 */

export function formatPrice(value: number | null | undefined, currency = "USD"): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPct(value: number | null | undefined, showSign = true): string {
  if (value === null || value === undefined) return "—";
  const sign = showSign && value > 0 ? "+" : "";
  return `${sign}${value.toFixed(1)}%`;
}

export function formatMultiple(value: number | null | undefined, suffix = "x"): string {
  if (value === null || value === undefined) return "—";
  return `${value.toFixed(1)}${suffix}`;
}

export function formatBillion(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `$${value.toFixed(1)}B`;
}

export function formatDate(dateString: string | null | undefined, format: "short" | "long" = "short"): string {
  if (!dateString) return "—";
  const date = new Date(dateString);
  if (format === "long") {
    return date.toLocaleDateString("ko-KR", { year: "numeric", month: "long", day: "numeric" });
  }
  return date.toLocaleDateString("ko-KR", { year: "numeric", month: "2-digit", day: "2-digit" });
}

export function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return new Intl.NumberFormat("en-US").format(value);
}

export function getPctColor(value: number | null | undefined): string {
  if (value === null || value === undefined) return "text-text-muted";
  if (value > 0) return "text-accent-green";
  if (value < 0) return "text-accent-red";
  return "text-text-secondary";
}

export function getDiscountLabel(pct: number): string {
  if (pct >= 30) return "대폭 할인";
  if (pct >= 20) return "할인";
  if (pct >= 10) return "소폭 할인";
  return "근접";
}
