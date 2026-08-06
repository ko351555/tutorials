"""SQLite-backed run state — the thing that makes `ystick run` resumable.

One row per (project_id, stage). The orchestrator consults this before
running anything and writes to it after every stage attempt, so a crash at
any point leaves an accurate, resumable record on disk.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from ystick.state.models import PENDING, STAGE_STATUSES, StageState

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    project_id TEXT NOT NULL,
    stage TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending',
    attempts INTEGER NOT NULL DEFAULT 0,
    last_error TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY (project_id, stage)
);
CREATE TABLE IF NOT EXISTS approvals (
    project_id TEXT NOT NULL,
    gate TEXT NOT NULL,
    decision_json TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    PRIMARY KEY (project_id, gate)
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StateStore:
    def __init__(self, db_path: Path):
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path
        with self._conn() as conn:
            conn.executescript(SCHEMA)

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def ensure_project(self, project_id: str, stage_order: list[str]) -> None:
        with self._conn() as conn:
            for stage in stage_order:
                conn.execute(
                    "INSERT OR IGNORE INTO runs (project_id, stage, status, attempts, updated_at) "
                    "VALUES (?, ?, ?, 0, ?)",
                    (project_id, stage, PENDING, _now()),
                )

    def get_status(self, project_id: str, stage: str) -> StageState:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM runs WHERE project_id = ? AND stage = ?",
                (project_id, stage),
            ).fetchone()
        if row is None:
            raise KeyError(f"no state for {project_id}/{stage}")
        return StageState(**dict(row))

    def list_stage_states(self, project_id: str, stage_order: list[str]) -> list[StageState]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM runs WHERE project_id = ?", (project_id,)
            ).fetchall()
        by_stage = {r["stage"]: StageState(**dict(r)) for r in rows}
        return [by_stage[s] for s in stage_order if s in by_stage]

    def set_status(
        self,
        project_id: str,
        stage: str,
        status: str,
        *,
        error: str | None = None,
        bump_attempts: bool = False,
    ) -> None:
        assert status in STAGE_STATUSES, f"invalid status {status!r}"
        with self._conn() as conn:
            if bump_attempts:
                conn.execute(
                    "UPDATE runs SET status=?, last_error=?, attempts=attempts+1, updated_at=? "
                    "WHERE project_id=? AND stage=?",
                    (status, error, _now(), project_id, stage),
                )
            else:
                conn.execute(
                    "UPDATE runs SET status=?, last_error=?, updated_at=? "
                    "WHERE project_id=? AND stage=?",
                    (status, error, _now(), project_id, stage),
                )

    def reset_from(self, project_id: str, stage_order: list[str], from_stage: str) -> None:
        idx = stage_order.index(from_stage)
        with self._conn() as conn:
            for stage in stage_order[idx:]:
                conn.execute(
                    "UPDATE runs SET status=?, attempts=0, last_error=NULL, updated_at=? "
                    "WHERE project_id=? AND stage=?",
                    (PENDING, _now(), project_id, stage),
                )

    def record_approval(self, project_id: str, gate: str, decision: dict) -> None:
        import json

        with self._conn() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO approvals (project_id, gate, decision_json, decided_at) "
                "VALUES (?, ?, ?, ?)",
                (project_id, gate, json.dumps(decision), _now()),
            )

    def get_approval(self, project_id: str, gate: str) -> dict | None:
        import json

        with self._conn() as conn:
            row = conn.execute(
                "SELECT decision_json FROM approvals WHERE project_id=? AND gate=?",
                (project_id, gate),
            ).fetchone()
        return json.loads(row["decision_json"]) if row else None
