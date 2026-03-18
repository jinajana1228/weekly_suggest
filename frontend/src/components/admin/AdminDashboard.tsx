"use client";

import { useState, useEffect, useTransition } from "react";
import type { ReviewTask, ReviewItem } from "@/types/schema";
import { formatDate } from "@/lib/formatters";
import Link from "next/link";

// ── Admin API (키 포함 fetch) ──────────────────────────────────

const ADMIN_KEY_STORAGE = "ws_admin_key";

async function adminFetch<T>(
  path: string,
  adminKey: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`/api/v1${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      "X-Admin-Key": adminKey,
      ...options?.headers,
    },
  });
  if (res.status === 403) throw new Error("FORBIDDEN");
  if (!res.ok) {
    const err = await res.text().catch(() => res.statusText);
    throw new Error(`API Error ${res.status}: ${err}`);
  }
  const json = await res.json();
  return json.data;
}

// ── Staging 타입 ─────────────────────────────────────────────

type NarrativeStatus = "APPROVED" | "DRAFT" | "PLACEHOLDER" | "MISSING";

type StagingTicker = {
  ticker:                  string;
  file:                    string;
  reviewer_approved:       boolean;
  reviewed_by:             string | null;
  reviewed_at:             string | null;
  publication_meta_status: string;
  narrative_blocks:        Record<string, NarrativeStatus>;
  all_approved:            boolean;
  model_id:                string;
};

type StagingStatus = {
  staging_dir_exists: boolean;
  draft_count:        number;
  ready_count:        number;
  tickers:            StagingTicker[];
};

type NarrativeBlock = {
  content: string;
  status:  NarrativeStatus;
};

// ── Preflight 타입 ───────────────────────────────────────────

type CheckStatus = "OK" | "WARN" | "ERROR";

type PreflightCheck = {
  id:     string;
  label:  string;
  status: CheckStatus;
  detail: string;
};

type PreflightTicker = {
  ticker:  string;
  overall: CheckStatus;
  checks:  PreflightCheck[];
};

type PreflightResult = {
  staging_dir_exists: boolean;
  checked_at:         string;
  summary: {
    total:       number;
    ok_count:    number;
    warn_count:  number;
    error_count: number;
    publishable: boolean;
  };
  tickers: PreflightTicker[];
};

type NarrativeData = {
  ticker:            string;
  blocks:            Record<string, NarrativeBlock>;
  reviewer_approved: boolean;
  model_id:          string;
};

const BLOCK_LABELS: Record<string, string> = {
  why_discounted:       "할인 원인",
  why_worth_revisiting: "재방문 근거",
  key_risks_narrative:  "핵심 리스크",
  investment_context:   "투자 맥락",
};

const NARRATIVE_STATUS_STYLE: Record<string, string> = {
  APPROVED:    "text-accent-green bg-green-950 border-green-900",
  DRAFT:       "text-yellow-500 bg-yellow-950/60 border-yellow-900",
  PLACEHOLDER: "text-accent-red bg-red-950 border-red-900",
  MISSING:     "text-text-muted bg-bg-overlay border-border-default",
};

// ── 상태 스타일 ───────────────────────────────────────────────

const ITEM_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  APPROVED: { label: "승인",   color: "text-accent-green border-green-900 bg-green-950" },
  PENDING:  { label: "대기",   color: "text-yellow-500 border-yellow-900 bg-yellow-950" },
  FLAGGED:  { label: "플래그", color: "text-accent-red border-red-900 bg-red-950" },
  REJECTED: { label: "반려",   color: "text-text-muted border-border-default bg-bg-overlay" },
};

const TASK_STATUS_CONFIG: Record<string, { label: string; color: string }> = {
  COMPLETED:   { label: "완료",          color: "text-accent-green" },
  IN_PROGRESS: { label: "진행 중",       color: "text-accent-gold" },
  OPEN:        { label: "대기",          color: "text-yellow-500" },
  ESCALATED:   { label: "에스컬레이션",  color: "text-accent-red" },
};

// ── AdminDashboard (완전 CSR) ─────────────────────────────────

export function AdminDashboard() {
  const [adminKey, setAdminKey]   = useState("");
  const [keyInput, setKeyInput]   = useState("");
  const [keyError, setKeyError]   = useState(false);
  const [tasks, setTasks]         = useState<ReviewTask[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [isPending, startTransition] = useTransition();

  // localStorage에서 키 복원
  useEffect(() => {
    const saved = localStorage.getItem(ADMIN_KEY_STORAGE);
    if (saved) {
      setAdminKey(saved);
    }
  }, []);

  // 키가 있으면 자동으로 태스크 로드
  useEffect(() => {
    if (!adminKey) return;
    loadTasks(adminKey);
  }, [adminKey]);

  async function loadTasks(key: string) {
    setLoading(true);
    setError(null);
    setKeyError(false);
    try {
      const data = await adminFetch<ReviewTask[]>("/admin/review-tasks", key);
      setTasks(data);
    } catch (e) {
      if (e instanceof Error && e.message === "FORBIDDEN") {
        setKeyError(true);
        setAdminKey("");
        localStorage.removeItem(ADMIN_KEY_STORAGE);
      } else {
        setError("데이터 로드 실패: " + (e instanceof Error ? e.message : String(e)));
      }
    } finally {
      setLoading(false);
    }
  }

  function handleKeySubmit(e: React.FormEvent) {
    e.preventDefault();
    const trimmed = keyInput.trim();
    if (!trimmed) return;
    localStorage.setItem(ADMIN_KEY_STORAGE, trimmed);
    setAdminKey(trimmed);
    setKeyInput("");
  }

  function handleLogout() {
    setAdminKey("");
    setTasks([]);
    localStorage.removeItem(ADMIN_KEY_STORAGE);
  }

  // ── 리뷰 아이템 상태 변경 ────────────────────────────────────

  function handleItemStatus(taskId: string, itemId: string, status: string) {
    startTransition(async () => {
      setError(null);
      try {
        const updated = await adminFetch<ReviewTask>(
          `/admin/review-tasks/${taskId}/items/${itemId}`,
          adminKey,
          { method: "PATCH", body: JSON.stringify({ status }) },
        );
        setTasks((prev) => prev.map((t) =>
          t.review_task_id === updated.review_task_id ? updated : t
        ));
      } catch (e) {
        setError("상태 변경 실패: " + (e instanceof Error ? e.message : String(e)));
      }
    });
  }

  // ── 태스크 최종 결정 ─────────────────────────────────────────

  function handleDecision(taskId: string, decision: "APPROVE" | "REJECT" | "HOLD") {
    const labels = { APPROVE: "발행 승인", REJECT: "반려", HOLD: "보류" };
    if (!confirm(`${labels[decision]}하시겠습니까?`)) return;

    startTransition(async () => {
      setError(null);
      try {
        const updated = await adminFetch<ReviewTask>(
          `/admin/review-tasks/${taskId}/decision`,
          adminKey,
          { method: "POST", body: JSON.stringify({ decision, decided_by: "editor" }) },
        );
        setTasks((prev) => prev.map((t) =>
          t.review_task_id === updated.review_task_id ? updated : t
        ));
      } catch (e) {
        setError("결정 처리 실패: " + (e instanceof Error ? e.message : String(e)));
      }
    });
  }

  // ── 통계 계산 ────────────────────────────────────────────────

  const allItems = tasks.flatMap((t) => t.review_items);
  const stats = {
    total:    allItems.length,
    approved: allItems.filter((i) => i.review_status === "APPROVED").length,
    pending:  allItems.filter((i) => i.review_status === "PENDING").length,
    flagged:  allItems.filter((i) => i.review_status === "FLAGGED").length,
  };

  // ── 키 미입력 상태 ────────────────────────────────────────────

  if (!adminKey) {
    return (
      <div className="max-w-md mx-auto px-4 sm:px-6 py-16">
        <div className="bg-bg-surface border border-border-default rounded-lg p-6">
          <h1 className="text-base font-semibold text-text-primary mb-1">검토 관리</h1>
          <p className="text-xs text-text-muted mb-6">Admin 키를 입력하세요.</p>

          {keyError && (
            <div className="mb-4 px-3 py-2 bg-red-950/40 border border-red-900 rounded text-xs text-accent-red">
              키가 올바르지 않습니다.
            </div>
          )}

          <form onSubmit={handleKeySubmit} className="space-y-3">
            <input
              type="password"
              value={keyInput}
              onChange={(e) => setKeyInput(e.target.value)}
              placeholder="X-Admin-Key 값 입력"
              className="w-full bg-bg-overlay border border-border-default rounded px-3 py-2 text-sm text-text-primary placeholder:text-text-muted focus:outline-none focus:border-zinc-500 font-mono"
            />
            <button
              type="submit"
              disabled={!keyInput.trim()}
              className="w-full text-sm py-2 rounded border border-accent-gold/50 text-accent-gold hover:bg-yellow-950/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              확인
            </button>
          </form>

          <p className="text-[10px] text-text-muted mt-4 text-center">
            키는 브라우저 localStorage에만 저장됩니다.
          </p>
        </div>
      </div>
    );
  }

  // ── 로딩 상태 ────────────────────────────────────────────────

  if (loading) {
    return (
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-16 text-center">
        <p className="text-text-muted text-sm">로딩 중...</p>
      </div>
    );
  }

  // ── 메인 대시보드 ─────────────────────────────────────────────

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* 헤더 */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold text-text-primary">검토 관리</h1>
          <p className="text-sm text-text-muted mt-1">리포트 발행 워크플로</p>
        </div>
        <button
          onClick={handleLogout}
          className="text-xs text-text-muted border border-border-default rounded px-3 py-1.5 bg-bg-surface hover:border-zinc-600 hover:text-text-secondary transition-colors"
        >
          로그아웃
        </button>
      </div>

      {/* 통계 바 */}
      <div className="grid grid-cols-4 gap-3 mb-6">
        {[
          { label: "전체",   value: stats.total,    color: "text-text-primary" },
          { label: "승인",   value: stats.approved, color: "text-accent-green" },
          { label: "대기",   value: stats.pending,  color: "text-yellow-500" },
          { label: "플래그", value: stats.flagged,  color: "text-accent-red" },
        ].map((s) => (
          <div key={s.label} className="bg-bg-surface border border-border-default rounded-lg px-4 py-3 text-center">
            <div className={`text-2xl font-mono font-bold ${s.color}`}>{s.value}</div>
            <div className="text-[10px] text-text-muted mt-0.5">{s.label}</div>
          </div>
        ))}
      </div>

      {/* 에러 메시지 */}
      {error && (
        <div className="mb-4 px-4 py-3 bg-red-950 border border-red-900 rounded-lg text-xs text-accent-red">
          {error}
        </div>
      )}

      {/* 로딩 힌트 */}
      {isPending && (
        <div className="mb-4 text-xs text-text-muted">처리 중...</div>
      )}

      {/* 발행 준비 상태 (Staging) */}
      <StagingDraftPanel adminKey={adminKey} />

      {/* Preflight 점검 패널 */}
      <PreflightPanel adminKey={adminKey} />

      {/* 태스크 목록 — 현재 검토 / 검토 이력 분리 */}
      {(() => {
        const ACTIVE_STATUSES   = ["OPEN", "IN_PROGRESS"];
        const activeTasks    = tasks.filter((t) => ACTIVE_STATUSES.includes(t.status));
        const historicalTasks = tasks.filter((t) => !ACTIVE_STATUSES.includes(t.status));

        return (
          <>
            {/* 현재 검토 작업 */}
            <div className="mb-2 flex items-center gap-2">
              <span className="text-xs font-semibold text-text-secondary uppercase tracking-wider">검토 작업</span>
              {activeTasks.length > 0 && (
                <span className="text-[10px] border border-yellow-900 text-yellow-500 bg-yellow-950/40 rounded px-1.5 py-0.5">
                  {activeTasks.length}건 진행 중
                </span>
              )}
            </div>

            {activeTasks.length === 0 ? (
              <div className="mb-6 text-center py-10 bg-bg-surface border border-border-default rounded-lg">
                <p className="text-text-muted text-sm">현재 검토 대기 중인 작업 없음</p>
                <p className="text-text-muted text-xs mt-1">
                  <code className="font-mono text-[10px] text-text-secondary">screen</code> 실행 후 스크리닝 결과가 이곳에 표시됩니다.
                </p>
              </div>
            ) : (
              <div className="mb-6 space-y-6">
                {activeTasks.map((task) => (
                  <TaskCard
                    key={task.review_task_id}
                    task={task}
                    onItemStatus={handleItemStatus}
                    onDecision={handleDecision}
                    isPending={isPending}
                  />
                ))}
              </div>
            )}

            {/* 검토 이력 */}
            {historicalTasks.length > 0 && (
              <HistoricalTaskSection
                tasks={historicalTasks}
                onItemStatus={handleItemStatus}
                onDecision={handleDecision}
                isPending={isPending}
              />
            )}
          </>
        );
      })()}
    </div>
  );
}

// ── HistoricalTaskSection ─────────────────────────────────────

function HistoricalTaskSection({
  tasks,
  onItemStatus,
  onDecision,
  isPending,
}: {
  tasks: ReviewTask[];
  onItemStatus: (taskId: string, itemId: string, status: string) => void;
  onDecision: (taskId: string, decision: "APPROVE" | "REJECT" | "HOLD") => void;
  isPending: boolean;
}) {
  const [expanded, setExpanded] = useState(false);

  // 최신 task(= 현재 발행본과 매칭)를 상단에 표시
  const sorted = [...tasks].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
  );

  return (
    <div>
      <button
        onClick={() => setExpanded((p) => !p)}
        className="mb-3 flex items-center gap-2 text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        <span className="font-semibold uppercase tracking-wider">검토 이력</span>
        <span className="border border-border-default rounded px-1.5 py-0.5 text-[10px]">
          {tasks.length}건
        </span>
        <span className="text-[10px] select-none">{expanded ? "▲ 접기" : "▼ 펼치기"}</span>
      </button>

      {expanded && (
        <div className="space-y-6">
          {sorted.map((task) => (
            <TaskCard
              key={task.review_task_id}
              task={task}
              onItemStatus={onItemStatus}
              onDecision={onDecision}
              isPending={isPending}
            />
          ))}
        </div>
      )}
    </div>
  );
}


// ── TaskCard ──────────────────────────────────────────────────

function TaskCard({
  task,
  onItemStatus,
  onDecision,
  isPending,
}: {
  task: ReviewTask;
  onItemStatus: (taskId: string, itemId: string, status: string) => void;
  onDecision: (taskId: string, decision: "APPROVE" | "REJECT" | "HOLD") => void;
  isPending: boolean;
}) {
  const statusConfig = TASK_STATUS_CONFIG[task.status] || TASK_STATUS_CONFIG.OPEN;
  const hasDecision  = !!task.publish_decision;

  return (
    <div className="bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      {/* 태스크 헤더 */}
      <div className="px-5 py-4 border-b border-border-default">
        <div className="flex items-start justify-between gap-4">
          <div>
            <div className="flex items-center gap-2 mb-1">
              <span className="font-mono text-xs text-text-secondary">{task.review_task_id}</span>
              <span className={`text-xs font-medium ${statusConfig.color}`}>{statusConfig.label}</span>
            </div>
            <div className="text-xs text-text-muted">
              리포트: {task.report_id} · 담당: {task.assigned_to || "미배정"}
            </div>
          </div>
          <div className="text-right text-xs text-text-muted shrink-0">
            <div>생성: {formatDate(task.created_at)}</div>
            {task.completed_at && <div>완료: {formatDate(task.completed_at)}</div>}
          </div>
        </div>
      </div>

      {/* 스크리닝 요약 */}
      <div className="px-5 py-3 border-b border-border-default bg-bg-overlay">
        <div className="flex items-center gap-6 text-xs text-text-muted">
          <span>후보: <span className="text-text-secondary font-medium">{task.screening_summary.total_candidates}개</span></span>
          <span>선택: <span className="text-accent-gold font-medium">{task.screening_summary.selected_count}개</span></span>
          <span>제외: <span className="text-text-secondary font-medium">{task.screening_summary.excluded_count}개</span></span>
          <span>실행: <span className="text-text-secondary">{formatDate(task.screening_summary.run_at)}</span></span>
        </div>
      </div>

      {/* 종목별 리뷰 */}
      <div className="px-5 py-4">
        <div className="text-[10px] text-text-muted uppercase tracking-wider mb-3">종목 검토</div>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {task.review_items.map((item) => (
            <ReviewItemCard
              key={item.report_item_id}
              item={item}
              taskId={task.review_task_id}
              reportId={task.report_id}
              onStatusChange={onItemStatus}
              disabled={isPending || hasDecision}
            />
          ))}
        </div>
      </div>

      {/* 최종 결정 버튼 or 결과 */}
      {hasDecision ? (
        <DecisionResult decision={task.publish_decision!} />
      ) : (
        <DecisionActions
          taskId={task.review_task_id}
          items={task.review_items}
          onDecision={onDecision}
          disabled={isPending}
        />
      )}
    </div>
  );
}

// ── ReviewItemCard ────────────────────────────────────────────

function ReviewItemCard({
  item,
  taskId,
  reportId,
  onStatusChange,
  disabled,
}: {
  item: ReviewItem;
  taskId: string;
  reportId: string;
  onStatusChange: (taskId: string, itemId: string, status: string) => void;
  disabled: boolean;
}) {
  const cfg = ITEM_STATUS_CONFIG[item.review_status] || ITEM_STATUS_CONFIG.PENDING;

  return (
    <div className="bg-bg-overlay border border-border-default rounded-lg p-3">
      <div className="flex items-center justify-between mb-2">
        <span className="font-mono text-sm font-bold text-text-primary">{item.ticker}</span>
        <span className={`text-[10px] border rounded px-1.5 py-0.5 font-medium ${cfg.color}`}>
          {cfg.label}
        </span>
      </div>

      <div className="flex items-center gap-2 text-[10px] text-text-muted mb-3">
        {item.data_quality_flag_count > 0 && (
          <span className="text-yellow-600">플래그 {item.data_quality_flag_count}건</span>
        )}
        {item.llm_narrative_approved && (
          <span className="text-accent-green">서술 승인</span>
        )}
      </div>

      <div className="flex gap-1 mb-2">
        {(["APPROVED", "FLAGGED", "REJECTED"] as const).map((s) => (
          <button
            key={s}
            disabled={disabled || item.review_status === s}
            onClick={() => onStatusChange(taskId, item.report_item_id, s)}
            className={`flex-1 text-[10px] py-1 rounded border transition-colors disabled:opacity-40 disabled:cursor-not-allowed
              ${item.review_status === s
                ? ITEM_STATUS_CONFIG[s].color + " opacity-100"
                : "text-text-muted border-border-default hover:border-zinc-600 hover:text-text-secondary bg-transparent"
              }`}
          >
            {ITEM_STATUS_CONFIG[s].label}
          </button>
        ))}
      </div>

      <Link
        href={`/report/${item.report_item_id}?report_id=${reportId}`}
        className="text-[10px] text-accent-blue hover:underline"
      >
        리포트 보기 →
      </Link>
    </div>
  );
}

// ── DecisionActions ───────────────────────────────────────────

function DecisionActions({
  taskId,
  items,
  onDecision,
  disabled,
}: {
  taskId: string;
  items: ReviewItem[];
  onDecision: (taskId: string, decision: "APPROVE" | "REJECT" | "HOLD") => void;
  disabled: boolean;
}) {
  const allApproved = items.every((i) => i.review_status === "APPROVED");
  const hasFlagged  = items.some((i)  => i.review_status === "FLAGGED");

  return (
    <div className="px-5 py-4 border-t border-border-default bg-bg-overlay">
      <div className="flex items-center justify-between gap-3">
        <div className="text-xs text-text-muted">
          {allApproved
            ? "모든 종목 검토 완료 — 발행 결정 가능"
            : hasFlagged
            ? "플래그 항목 검토 후 결정하세요"
            : "검토를 완료한 후 결정하세요"}
        </div>
        <div className="flex gap-2">
          <button
            disabled={disabled}
            onClick={() => onDecision(taskId, "HOLD")}
            className="text-xs px-3 py-1.5 rounded border border-border-default text-text-muted hover:border-zinc-600 hover:text-text-secondary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            보류
          </button>
          <button
            disabled={disabled}
            onClick={() => onDecision(taskId, "REJECT")}
            className="text-xs px-3 py-1.5 rounded border border-red-900 text-accent-red hover:bg-red-950 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            반려
          </button>
          <button
            disabled={disabled || !allApproved}
            onClick={() => onDecision(taskId, "APPROVE")}
            className="text-xs px-3 py-1.5 rounded border border-green-900 text-accent-green hover:bg-green-950 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            발행 승인
          </button>
        </div>
      </div>
    </div>
  );
}

// ── DecisionResult ────────────────────────────────────────────

function DecisionResult({
  decision,
}: {
  decision: NonNullable<ReviewTask["publish_decision"]>;
}) {
  const isApprove = decision.decision === "APPROVE";
  return (
    <div className={`px-5 py-3 border-t border-border-default ${isApprove ? "bg-green-950/20" : "bg-red-950/20"}`}>
      <div className="flex items-center gap-3 text-xs">
        <span className={`font-medium ${isApprove ? "text-accent-green" : "text-accent-red"}`}>
          {isApprove ? "발행 승인" : decision.decision === "REJECT" ? "반려" : "보류"}
        </span>
        <span className="text-text-muted">
          {decision.decided_by} · {formatDate(decision.decided_at)}
        </span>
        {decision.reason && (
          <span className="text-text-muted">— {decision.reason}</span>
        )}
      </div>
    </div>
  );
}

// ── StagingDraftPanel ─────────────────────────────────────────

function StagingDraftPanel({ adminKey }: { adminKey: string }) {
  const [status,   setStatus]   = useState<StagingStatus | null>(null);
  const [loading,  setLoading]  = useState(false);
  const [error,    setError]    = useState<string | null>(null);
  const [approving, setApproving] = useState<string | null>(null);

  useEffect(() => {
    if (adminKey) loadStatus(adminKey);
  }, [adminKey]);

  async function loadStatus(key: string) {
    setLoading(true);
    setError(null);
    try {
      const data = await adminFetch<StagingStatus>("/admin/staging/review-status", key);
      setStatus(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  async function handleApprove(ticker: string) {
    setApproving(ticker);
    setError(null);
    try {
      await adminFetch(`/admin/staging/${ticker}/approve-narrative`, adminKey, { method: "POST" });
      await loadStatus(adminKey);
    } catch (e) {
      setError(`${ticker} 승인 실패: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setApproving(null);
    }
  }

  if (loading && !status) {
    return (
      <div className="mb-6 bg-bg-surface border border-border-default rounded-lg px-5 py-4">
        <p className="text-xs text-text-muted">발행 준비 상태 로딩 중...</p>
      </div>
    );
  }

  if (!status || !status.staging_dir_exists || status.draft_count === 0) {
    return (
      <div className="mb-6 bg-bg-surface border border-border-default rounded-lg px-5 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-semibold text-text-secondary">발행 준비 (Staging)</h2>
            <p className="text-xs text-text-muted mt-1">
              draft 없음 — <code className="font-mono text-text-secondary text-[10px]">screen</code> 실행 후 확인하세요
            </p>
          </div>
          <button
            onClick={() => loadStatus(adminKey)}
            disabled={loading}
            className="text-[10px] text-text-muted border border-border-default rounded px-2 py-1 hover:border-zinc-600 hover:text-text-secondary transition-colors disabled:opacity-40"
          >
            새로고침
          </button>
        </div>
      </div>
    );
  }

  const allReady     = status.ready_count === status.draft_count;
  const readyColor   = allReady
    ? "text-accent-green border-green-900"
    : status.ready_count > 0
    ? "text-accent-gold border-yellow-900"
    : "text-text-muted border-border-default";

  return (
    <div className="mb-6 bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      {/* 헤더 */}
      <div className="px-5 py-3 border-b border-border-default bg-bg-overlay flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-secondary">발행 준비 (Staging)</h2>
          <p className="text-[10px] text-text-muted mt-0.5">
            발행 가능 기준: 4개 narrative 블록 모두 APPROVED
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className={`text-xs font-mono font-bold border rounded px-2 py-0.5 ${readyColor}`}>
            {status.ready_count}/{status.draft_count} 준비됨
          </span>
          <button
            onClick={() => loadStatus(adminKey)}
            disabled={loading}
            className="text-[10px] text-text-muted border border-border-default rounded px-2 py-1 hover:border-zinc-600 hover:text-text-secondary transition-colors disabled:opacity-40"
          >
            새로고침
          </button>
        </div>
      </div>

      {/* 에러 */}
      {error && (
        <div className="mx-5 mt-3 px-3 py-2 bg-red-950/40 border border-red-900 rounded text-xs text-accent-red">
          {error}
        </div>
      )}

      {/* 종목별 카드 */}
      <div className="px-5 py-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
          {status.tickers.map((t) => (
            <StagingTickerCard
              key={t.ticker}
              ticker={t}
              adminKey={adminKey}
              onApprove={handleApprove}
              approving={approving === t.ticker}
              onRefresh={() => loadStatus(adminKey)}
            />
          ))}
        </div>
      </div>

      {/* 하단 상태 */}
      <div className={`px-5 py-3 border-t border-border-default ${allReady ? "bg-green-950/20" : "bg-bg-overlay"}`}>
        {allReady ? (
          <p className="text-xs text-accent-green">
            모든 종목 narrative 검토 완료 — preflight 후 prepare 실행 가능
          </p>
        ) : (
          <p className="text-xs text-text-muted">
            {status.draft_count - status.ready_count}개 종목 검토 미완.
            {" "}각 종목 카드의 승인 버튼 또는 CLI:{" "}
            <code className="font-mono text-text-secondary text-[10px]">
              review --approve-all
            </code>
          </p>
        )}
      </div>
    </div>
  );
}

// ── StagingTickerCard ─────────────────────────────────────────

function StagingTickerCard({
  ticker: t,
  adminKey,
  onApprove,
  approving,
  onRefresh,
}: {
  ticker:    StagingTicker;
  adminKey:  string;
  onApprove: (ticker: string) => void;
  approving: boolean;
  onRefresh: () => void;
}) {
  const BLOCKS = [
    "why_discounted", "why_worth_revisiting",
    "key_risks_narrative", "investment_context",
  ] as const;

  const [expanded,        setExpanded]        = useState(false);
  const [narrative,       setNarrative]       = useState<NarrativeData | null>(null);
  const [localEdits,      setLocalEdits]      = useState<Record<string, string>>({});
  const [loadingNarrative,setLoadingNarrative]= useState(false);
  const [savingBlock,     setSavingBlock]     = useState<string | null>(null);
  const [saveError,       setSaveError]       = useState<string | null>(null);

  async function loadNarrative() {
    setLoadingNarrative(true);
    setSaveError(null);
    try {
      const data = await adminFetch<NarrativeData>(
        `/admin/staging/${t.ticker}/narrative`, adminKey,
      );
      setNarrative(data);
      const edits: Record<string, string> = {};
      BLOCKS.forEach((blk) => { edits[blk] = data.blocks[blk]?.content ?? ""; });
      setLocalEdits(edits);
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoadingNarrative(false);
    }
  }

  function handleToggleExpand() {
    if (!expanded && !narrative) loadNarrative();
    setExpanded((prev) => !prev);
  }

  async function handleSave(blockKey: string, approve: boolean) {
    const saveKey = blockKey + (approve ? "_approve" : "");
    setSavingBlock(saveKey);
    setSaveError(null);
    try {
      await adminFetch(
        `/admin/staging/${t.ticker}/narrative`,
        adminKey,
        { method: "PATCH", body: JSON.stringify({ block: blockKey, content: localEdits[blockKey] ?? "", approve }) },
      );
      await loadNarrative();
      onRefresh();
    } catch (e) {
      setSaveError(`저장 실패: ${e instanceof Error ? e.message : String(e)}`);
    } finally {
      setSavingBlock(null);
    }
  }

  return (
    <div className={`bg-bg-overlay border rounded-lg overflow-hidden ${t.all_approved ? "border-green-900" : "border-border-default"}`}>
      {/* 종목 헤더 — 클릭으로 편집 패널 토글 */}
      <div
        className="flex items-center justify-between p-3 cursor-pointer hover:bg-bg-surface transition-colors"
        onClick={handleToggleExpand}
      >
        <div className="flex items-center gap-2">
          <span className="font-mono text-sm font-bold text-text-primary">{t.ticker}</span>
          <span className={`text-[10px] border rounded px-1.5 py-0.5 font-medium ${
            t.all_approved
              ? "text-accent-green border-green-900 bg-green-950"
              : "text-yellow-500 border-yellow-900 bg-yellow-950/60"
          }`}>
            {t.all_approved ? "검토완료" : "검토중"}
          </span>
        </div>
        <span className="text-[10px] text-text-muted select-none">{expanded ? "▲" : "▼ 편집"}</span>
      </div>

      {/* narrative 블록 상태 요약 */}
      <div className="px-3 pb-2 space-y-1">
        {BLOCKS.map((blk) => {
          const s = (t.narrative_blocks[blk] || "MISSING") as NarrativeStatus;
          return (
            <div key={blk} className="flex items-center justify-between gap-2">
              <span className="text-[10px] text-text-muted truncate">{BLOCK_LABELS[blk]}</span>
              <span className={`text-[9px] border rounded px-1 py-0.5 shrink-0 ${NARRATIVE_STATUS_STYLE[s] ?? NARRATIVE_STATUS_STYLE.MISSING}`}>
                {s}
              </span>
            </div>
          );
        })}
      </div>

      {/* 검토자 정보 */}
      <div className="px-3 pb-2 text-[10px] text-text-muted">
        {t.reviewed_by
          ? <span className="text-text-secondary">검토: {t.reviewed_by}</span>
          : <span>검토자 미지정</span>
        }
        {t.model_id === "rule-based-v1" && (
          <span className="ml-2 opacity-60">[rule-based]</span>
        )}
      </div>

      {/* 인라인 편집 패널 */}
      {expanded && (
        <div className="border-t border-border-default px-3 py-3 space-y-4">
          {loadingNarrative && (
            <p className="text-xs text-text-muted">로딩 중...</p>
          )}
          {saveError && (
            <div className="px-3 py-2 bg-red-950/40 border border-red-900 rounded text-xs text-accent-red">
              {saveError}
            </div>
          )}
          {narrative && BLOCKS.map((blk) => {
            const blockStatus = narrative.blocks[blk]?.status ?? "MISSING";
            const isSavingThis    = savingBlock === blk;
            const isApprovingThis = savingBlock === blk + "_approve";
            return (
              <div key={blk} className="space-y-1.5">
                <div className="flex items-center justify-between">
                  <span className="text-[11px] text-text-secondary font-medium">{BLOCK_LABELS[blk]}</span>
                  <span className={`text-[9px] border rounded px-1 py-0.5 ${NARRATIVE_STATUS_STYLE[blockStatus] ?? NARRATIVE_STATUS_STYLE.MISSING}`}>
                    {blockStatus}
                  </span>
                </div>
                <textarea
                  value={localEdits[blk] ?? ""}
                  onChange={(e) => setLocalEdits((prev) => ({ ...prev, [blk]: e.target.value }))}
                  rows={4}
                  className="w-full bg-bg-surface border border-border-default rounded px-2 py-1.5 text-xs text-text-primary placeholder:text-text-muted focus:outline-none focus:border-zinc-500 resize-y font-mono leading-relaxed"
                />
                <div className="flex gap-1.5 justify-end">
                  <button
                    disabled={!!savingBlock}
                    onClick={() => handleSave(blk, false)}
                    className="text-[10px] px-2.5 py-1 rounded border border-border-default text-text-muted hover:border-zinc-600 hover:text-text-secondary transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isSavingThis ? "저장 중..." : "저장"}
                  </button>
                  <button
                    disabled={!!savingBlock}
                    onClick={() => handleSave(blk, true)}
                    className="text-[10px] px-2.5 py-1 rounded border border-green-900 text-accent-green hover:bg-green-950 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
                  >
                    {isApprovingThis ? "처리 중..." : "저장 + 승인"}
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 전체 승인 버튼 */}
      {!t.all_approved && (
        <div className="px-3 pb-3">
          <button
            onClick={() => onApprove(t.ticker)}
            disabled={approving}
            className="w-full text-[10px] py-1 rounded border border-green-900 text-accent-green hover:bg-green-950 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            {approving ? "처리 중..." : "narrative 전체 승인"}
          </button>
        </div>
      )}
    </div>
  );
}

// ── PreflightPanel ────────────────────────────────────────────

const CHECK_STATUS_STYLE: Record<CheckStatus, string> = {
  OK:    "text-accent-green border-green-900 bg-green-950",
  WARN:  "text-accent-gold border-yellow-900 bg-yellow-950/60",
  ERROR: "text-accent-red border-red-900 bg-red-950",
};

const CHECK_STATUS_DOT: Record<CheckStatus, string> = {
  OK:    "bg-accent-green",
  WARN:  "bg-accent-gold",
  ERROR: "bg-accent-red",
};

function PreflightPanel({ adminKey }: { adminKey: string }) {
  const [result,  setResult]  = useState<PreflightResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error,   setError]   = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Record<string, boolean>>({});

  async function runPreflight() {
    setLoading(true);
    setError(null);
    try {
      const data = await adminFetch<PreflightResult>("/admin/staging/preflight", adminKey);
      setResult(data);
      setExpanded({});
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  }

  function toggleTicker(ticker: string) {
    setExpanded((prev) => ({ ...prev, [ticker]: !prev[ticker] }));
  }

  return (
    <div className="mb-6 bg-bg-surface border border-border-default rounded-lg overflow-hidden">
      {/* 헤더 */}
      <div className="px-5 py-3 border-b border-border-default bg-bg-overlay flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-text-secondary">Preflight 점검</h2>
          <p className="text-[10px] text-text-muted mt-0.5">
            차트 파일 · Narrative · 선정 유형 · 미완성 마커 검사
          </p>
        </div>
        <button
          onClick={runPreflight}
          disabled={loading}
          className="text-[10px] px-3 py-1.5 rounded border border-accent-gold/50 text-accent-gold hover:bg-yellow-950/30 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          {loading ? "점검 중..." : "점검 실행"}
        </button>
      </div>

      {/* 에러 */}
      {error && (
        <div className="mx-5 mt-3 px-3 py-2 bg-red-950/40 border border-red-900 rounded text-xs text-accent-red">
          {error}
        </div>
      )}

      {/* 미실행 상태 */}
      {!result && !loading && !error && (
        <div className="px-5 py-6 text-center">
          <p className="text-xs text-text-muted">
            "점검 실행" 버튼을 눌러 발행 전 상태를 확인하세요.
          </p>
        </div>
      )}

      {/* 로딩 */}
      {loading && (
        <div className="px-5 py-6 text-center">
          <p className="text-xs text-text-muted">staging 파일 점검 중...</p>
        </div>
      )}

      {/* 결과 */}
      {result && !loading && (
        <>
          {/* staging 없음 */}
          {!result.staging_dir_exists || result.tickers.length === 0 ? (
            <div className="px-5 py-4 text-xs text-text-muted">
              staging 파일 없음 — <code className="font-mono text-[10px] text-text-secondary">screen</code> 실행 후 재점검하세요.
            </div>
          ) : (
            <>
              {/* 요약 바 */}
              <div className={`px-5 py-3 border-b border-border-default flex items-center justify-between gap-4 ${
                result.summary.publishable ? "bg-green-950/20" : "bg-red-950/10"
              }`}>
                <div className="flex items-center gap-2">
                  <span className={`text-xs font-semibold ${
                    result.summary.publishable ? "text-accent-green" : "text-accent-red"
                  }`}>
                    {result.summary.publishable ? "발행 가능" : "발행 불가"}
                  </span>
                  <span className="text-[10px] text-text-muted">
                    {result.tickers.length}개 종목
                  </span>
                </div>
                <div className="flex items-center gap-3 text-[10px]">
                  <span className="text-accent-green">OK {result.summary.ok_count}</span>
                  <span className="text-accent-gold">WARN {result.summary.warn_count}</span>
                  <span className="text-accent-red">ERROR {result.summary.error_count}</span>
                  <span className="text-text-muted border-l border-border-default pl-3">
                    {result.checked_at.replace("T", " ").replace("Z", " UTC")}
                  </span>
                </div>
              </div>

              {/* 종목별 결과 */}
              <div className="px-5 py-4 space-y-2">
                {result.tickers.map((t) => (
                  <div key={t.ticker} className={`border rounded-lg overflow-hidden ${
                    t.overall === "ERROR"
                      ? "border-red-900"
                      : t.overall === "WARN"
                      ? "border-yellow-900"
                      : "border-green-900"
                  }`}>
                    {/* 종목 행 — 클릭으로 체크 상세 토글 */}
                    <div
                      className="flex items-center justify-between px-3 py-2.5 cursor-pointer hover:bg-bg-overlay transition-colors"
                      onClick={() => toggleTicker(t.ticker)}
                    >
                      <div className="flex items-center gap-2.5">
                        <span className="font-mono text-sm font-bold text-text-primary">{t.ticker}</span>
                        <span className={`text-[9px] border rounded px-1.5 py-0.5 font-medium ${CHECK_STATUS_STYLE[t.overall]}`}>
                          {t.overall}
                        </span>
                        {/* 체크 요약 점 */}
                        <div className="flex items-center gap-1">
                          {t.checks.map((c) => (
                            <span
                              key={c.id}
                              title={`${c.label}: ${c.detail}`}
                              className={`w-1.5 h-1.5 rounded-full ${CHECK_STATUS_DOT[c.status]}`}
                            />
                          ))}
                        </div>
                      </div>
                      <span className="text-[10px] text-text-muted select-none">
                        {expanded[t.ticker] ? "▲" : "▼"}
                      </span>
                    </div>

                    {/* 체크 상세 */}
                    {expanded[t.ticker] && (
                      <div className="border-t border-border-default bg-bg-overlay divide-y divide-border-default/50">
                        {t.checks.map((c) => (
                          <div key={c.id} className="flex items-start gap-3 px-3 py-2">
                            <span className={`text-[9px] border rounded px-1.5 py-0.5 font-medium shrink-0 mt-0.5 ${CHECK_STATUS_STYLE[c.status]}`}>
                              {c.status}
                            </span>
                            <div className="min-w-0">
                              <div className="text-[10px] text-text-secondary font-medium">{c.label}</div>
                              <div className="text-[10px] text-text-muted font-mono mt-0.5 break-all">{c.detail}</div>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </>
          )}
        </>
      )}
    </div>
  );
}
