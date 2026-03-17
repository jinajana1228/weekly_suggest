import type {
  ReportEdition,
  StockReport,
  ArchiveEntry,
  ChartDataPackage,
  ReviewTask,
  ApiResponse,
} from "@/types/schema";

// SSR: 직접 백엔드 호출 / CSR: Next.js rewrites 경유
const API_BASE =
  process.env.NEXT_PUBLIC_API_URL ||
  (typeof window === "undefined"
    ? "http://localhost:8000/api/v1"
    : "/api/v1");

// ── GET (SSR/CSR 공용, 5분 캐시) ────────────────────────────────
async function fetchApi<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    next: { revalidate: 300 },
  });
  if (!res.ok) throw new Error(`API Error: ${res.status} ${path}`);
  const json: ApiResponse<T> = await res.json();
  return json.data;
}

// ── Mutation (CSR 전용 — 항상 /api/v1 경유) ──────────────────────
async function mutateApi<T>(
  path: string,
  method: "POST" | "PATCH" | "PUT" | "DELETE",
  body?: unknown,
): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API ${method} Error: ${res.status} ${path} — ${err}`);
  }
  const json: ApiResponse<T> = await res.json();
  return json.data;
}

export const apiClient = {
  // ── 리포트 ─────────────────────────────────────────────────
  getLatestReport: () => fetchApi<ReportEdition>("/reports/latest"),

  getStockReport: (reportId: string, ticker: string) =>
    fetchApi<StockReport>(`/reports/${reportId}/stocks/${ticker}`),

  // ── 아카이브 ────────────────────────────────────────────────
  getArchive: () => fetchApi<ArchiveEntry[]>("/archive"),

  getArchiveEdition: (editionNumber: number) =>
    fetchApi<ReportEdition>(`/archive/${editionNumber}`),

  // ── 차트 ────────────────────────────────────────────────────
  getChartData: (ticker: string, periodDays: number = 365) =>
    fetchApi<ChartDataPackage>(`/chart/${ticker}?period_days=${periodDays}`),

  // ── Admin (읽기) ─────────────────────────────────────────────
  getReviewTasks: () => fetchApi<ReviewTask[]>("/admin/review-tasks"),

  // ── Admin (쓰기 — CSR 전용) ──────────────────────────────────
  updateReviewItemStatus: (
    taskId: string,
    itemId: string,
    status: string,
    notes?: string,
  ) =>
    mutateApi<ReviewTask>(
      `/admin/review-tasks/${taskId}/items/${itemId}`,
      "PATCH",
      { status, notes },
    ),

  setTaskDecision: (
    taskId: string,
    decision: string,
    decidedBy = "editor_01",
    reason?: string,
  ) =>
    mutateApi<ReviewTask>(`/admin/review-tasks/${taskId}/decision`, "POST", {
      decision,
      decided_by: decidedBy,
      reason,
    }),
};
