"""
SQLite 기반 상태 저장소 — review task / item / edition status

역할 분리:
  FileStore  → 정적 JSON (mock 리포트 데이터) 읽기
  StateStore → 동적 상태 (리뷰 상태, 승인, 에디션 발행) 읽기/쓰기
"""
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from app.core.config import settings


def _db_path() -> Path:
    """SQLite DB 경로 결정.

    우선순위:
    1. STATE_DB_PATH 환경변수 (절대경로) — Railway Volume 등 외부 경로 지정 시
    2. __file__ 기반 자동 해석 — 로컬 개발 및 Railway 표준 배포 구조
       __file__ = backend/app/storage/state_store.py (×4 parent = weekly_suggest/)
    """
    configured = settings.STATE_DB_PATH
    if configured:
        p = Path(configured)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p

    # __file__ 기반 자동 해석
    # 로컬:   weekly_suggest/data/state.db
    # Railway(/app/): /app/data/state.db  (배포 루트 = weekly_suggest/)
    project_root = Path(__file__).resolve().parent.parent.parent.parent
    data_dir = project_root / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "state.db"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateStore:
    def __init__(self, db_path: Path | None = None):
        self._db = db_path or _db_path()
        self._init_db()

    # ── DB 초기화 ───────────────────────────────────────────────

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS review_tasks (
                    task_id     TEXT PRIMARY KEY,
                    report_id   TEXT NOT NULL,
                    status      TEXT NOT NULL DEFAULT 'OPEN',
                    assigned_to TEXT,
                    created_at  TEXT NOT NULL,
                    completed_at TEXT,
                    screening_summary TEXT NOT NULL DEFAULT '{}',
                    decision    TEXT
                );

                CREATE TABLE IF NOT EXISTS review_items (
                    item_id     TEXT NOT NULL,
                    task_id     TEXT NOT NULL,
                    ticker      TEXT NOT NULL,
                    review_status TEXT NOT NULL DEFAULT 'PENDING',
                    reviewer_notes TEXT,
                    data_quality_flag_count INTEGER NOT NULL DEFAULT 0,
                    llm_narrative_approved  INTEGER NOT NULL DEFAULT 0,
                    updated_at  TEXT,
                    PRIMARY KEY (item_id, task_id)
                );

                CREATE TABLE IF NOT EXISTS edition_status (
                    report_id   TEXT PRIMARY KEY,
                    status      TEXT NOT NULL DEFAULT 'DRAFT',
                    published_at TEXT,
                    updated_at  TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS editions (
                    report_id      TEXT PRIMARY KEY,
                    edition_number INTEGER NOT NULL,
                    issue_type     TEXT NOT NULL DEFAULT 'REGULAR_BIWEEKLY',
                    data_as_of     TEXT,
                    created_at     TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS latest_pointer (
                    id         INTEGER PRIMARY KEY CHECK (id = 1),
                    report_id  TEXT NOT NULL,
                    set_at     TEXT NOT NULL,
                    set_by     TEXT NOT NULL DEFAULT 'system'
                );
            """)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db)
        conn.row_factory = sqlite3.Row
        return conn

    # ── 시드: FileStore mock 데이터 → DB 초기값 ─────────────────

    def seed_from_mock(self, mock_tasks: list[dict]) -> None:
        """DB가 비어있을 때 mock task 목록을 seed."""
        with self._conn() as conn:
            existing = conn.execute(
                "SELECT COUNT(*) FROM review_tasks"
            ).fetchone()[0]
            if existing > 0:
                return  # 이미 시드됨

            for task in mock_tasks:
                conn.execute(
                    """INSERT OR IGNORE INTO review_tasks
                       (task_id, report_id, status, assigned_to,
                        created_at, completed_at, screening_summary, decision)
                       VALUES (?,?,?,?,?,?,?,?)""",
                    (
                        task["review_task_id"],
                        task["report_id"],
                        task.get("status", "OPEN"),
                        task.get("assigned_to"),
                        task.get("created_at", _now()),
                        task.get("completed_at"),
                        json.dumps(task.get("screening_summary", {})),
                        json.dumps(task.get("publish_decision")) if task.get("publish_decision") else None,
                    ),
                )
                for item in task.get("review_items", []):
                    conn.execute(
                        """INSERT OR IGNORE INTO review_items
                           (item_id, task_id, ticker, review_status,
                            reviewer_notes, data_quality_flag_count,
                            llm_narrative_approved, updated_at)
                           VALUES (?,?,?,?,?,?,?,?)""",
                        (
                            item["report_item_id"],
                            task["review_task_id"],
                            item["ticker"],
                            item.get("review_status", "PENDING"),
                            item.get("reviewer_notes"),
                            item.get("data_quality_flag_count", 0),
                            1 if item.get("llm_narrative_approved") else 0,
                            _now(),
                        ),
                    )

    # ── 조회 ────────────────────────────────────────────────────

    def get_all_tasks(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM review_tasks ORDER BY created_at DESC"
            ).fetchall()
            result = []
            for r in rows:
                task = dict(r)
                task["screening_summary"] = json.loads(task["screening_summary"] or "{}")
                task["publish_decision"] = (
                    json.loads(task["decision"]) if task.get("decision") else None
                )
                task.pop("decision", None)

                items = conn.execute(
                    "SELECT * FROM review_items WHERE task_id = ?",
                    (task["task_id"],),
                ).fetchall()
                task["review_task_id"] = task.pop("task_id")
                task["review_items"] = [
                    {
                        "report_item_id": i["item_id"],
                        "ticker": i["ticker"],
                        "review_status": i["review_status"],
                        "reviewer_notes": i["reviewer_notes"],
                        "data_quality_flag_count": i["data_quality_flag_count"],
                        "llm_narrative_approved": bool(i["llm_narrative_approved"]),
                    }
                    for i in items
                ]
                result.append(task)
            return result

    def get_task(self, task_id: str) -> Optional[dict]:
        tasks = self.get_all_tasks()
        return next((t for t in tasks if t["review_task_id"] == task_id), None)

    # ── 업데이트 ─────────────────────────────────────────────────

    def update_review_item(
        self,
        task_id: str,
        item_id: str,
        status: str,
        notes: str | None = None,
    ) -> bool:
        with self._conn() as conn:
            result = conn.execute(
                """UPDATE review_items
                   SET review_status = ?,
                       reviewer_notes = COALESCE(?, reviewer_notes),
                       updated_at = ?
                   WHERE task_id = ? AND item_id = ?""",
                (status, notes, _now(), task_id, item_id),
            )
            return result.rowcount > 0

    def set_task_decision(
        self,
        task_id: str,
        decision: str,
        decided_by: str = "editor_01",
        reason: str | None = None,
    ) -> bool:
        payload = {
            "decision": decision,
            "decided_by": decided_by,
            "decided_at": _now(),
            "reason": reason,
        }
        new_status = (
            "COMPLETED" if decision == "APPROVE"
            else "ESCALATED" if decision == "HOLD"
            else "COMPLETED"  # REJECT도 COMPLETED
        )
        with self._conn() as conn:
            result = conn.execute(
                """UPDATE review_tasks
                   SET decision = ?, status = ?,
                       completed_at = CASE WHEN ? IN ('APPROVE','REJECT') THEN ? ELSE completed_at END
                   WHERE task_id = ?""",
                (json.dumps(payload), new_status, decision, _now(), task_id),
            )
            return result.rowcount > 0

    def upsert_task(self, task: dict) -> None:
        """신규 screening 결과를 review task로 등록."""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO review_tasks
                   (task_id, report_id, status, assigned_to,
                    created_at, screening_summary)
                   VALUES (?,?,?,?,?,?)""",
                (
                    task["review_task_id"],
                    task["report_id"],
                    task.get("status", "OPEN"),
                    task.get("assigned_to"),
                    task.get("created_at", _now()),
                    json.dumps(task.get("screening_summary", {})),
                ),
            )
            for item in task.get("review_items", []):
                conn.execute(
                    """INSERT OR IGNORE INTO review_items
                       (item_id, task_id, ticker, review_status,
                        data_quality_flag_count, llm_narrative_approved, updated_at)
                       VALUES (?,?,?,?,?,?,?)""",
                    (
                        item["report_item_id"],
                        task["review_task_id"],
                        item["ticker"],
                        "PENDING",
                        0, 0, _now(),
                    ),
                )

    def update_edition_status(
        self,
        report_id: str,
        status: str,
    ) -> None:
        now = _now()
        published_at = now if status == "PUBLISHED" else None
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO edition_status
                   (report_id, status, published_at, updated_at)
                   VALUES (?,?,?,?)""",
                (report_id, status, published_at, now),
            )

    def get_edition_status(self, report_id: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT status FROM edition_status WHERE report_id = ?",
                (report_id,),
            ).fetchone()
            return row["status"] if row else None

    # ── latest_pointer ───────────────────────────────────────────

    def get_latest_pointer(self) -> Optional[str]:
        """현재 PUBLISHED 최신 에디션의 report_id 반환."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT report_id FROM latest_pointer WHERE id = 1"
            ).fetchone()
            return row["report_id"] if row else None

    def set_latest_pointer(
        self, report_id: str, set_by: str = "system"
    ) -> None:
        """최신 발행 에디션 포인터 갱신 (항상 id=1 단일 행)."""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR REPLACE INTO latest_pointer (id, report_id, set_at, set_by)
                   VALUES (1, ?, ?, ?)""",
                (report_id, _now(), set_by),
            )

    # ── editions 등록/조회 ───────────────────────────────────────

    def register_edition(
        self,
        report_id: str,
        edition_number: int,
        issue_type: str = "REGULAR_BIWEEKLY",
        data_as_of: Optional[str] = None,
    ) -> None:
        """새 에디션 메타데이터 등록."""
        with self._conn() as conn:
            conn.execute(
                """INSERT OR IGNORE INTO editions
                   (report_id, edition_number, issue_type, data_as_of, created_at)
                   VALUES (?,?,?,?,?)""",
                (report_id, edition_number, issue_type, data_as_of, _now()),
            )

    def get_next_edition_number(self) -> int:
        """다음 발행 에디션 번호 반환 (현재 max + 1, 없으면 1)."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT MAX(edition_number) AS max_num FROM editions"
            ).fetchone()
            current = row["max_num"] if row["max_num"] is not None else 0
            return current + 1

    def get_edition_meta(self, report_id: str) -> Optional[dict]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM editions WHERE report_id = ?", (report_id,)
            ).fetchone()
            return dict(row) if row else None


state_store = StateStore()
