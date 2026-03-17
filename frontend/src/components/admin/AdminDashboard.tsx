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

      {/* 태스크 목록 */}
      {tasks.length === 0 ? (
        <div className="text-center py-16 bg-bg-surface border border-border-default rounded-lg">
          <p className="text-text-muted text-sm">검토 대기 중인 작업 없음</p>
        </div>
      ) : (
        <div className="space-y-6">
          {tasks.map((task) => (
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
