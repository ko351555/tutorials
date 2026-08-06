from __future__ import annotations

from dataclasses import dataclass


PENDING = "pending"
RUNNING = "running"
AWAITING_APPROVAL = "awaiting_approval"
DONE = "done"
FAILED = "failed"

TERMINAL_OK = {DONE}
STAGE_STATUSES = {PENDING, RUNNING, AWAITING_APPROVAL, DONE, FAILED}


@dataclass
class StageState:
    project_id: str
    stage: str
    status: str
    attempts: int
    last_error: str | None
    updated_at: str
