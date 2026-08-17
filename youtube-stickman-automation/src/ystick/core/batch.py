"""Batch runner — creates and fully runs every project in a weekly_plan.yaml
without any manual approval steps. Gates are auto-resolved:
  topic_selection  → picks idea #0 (Stage 1 seeds from the title, so #0 is
                      always the best match)
  script_review    → auto-approved (proceeds without editing)
  storyboard_review→ auto-approved
  image_upload     → skipped in batch mode (manual provider not compatible)
  final_review     → auto-approved (fires off as-is)

This is intentionally a "fire and forget" flow. For content that needs human
eyes before publishing, run via the normal UI flow instead.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator

import yaml

from ystick.core.orchestrator import GATE_AFTER_STAGE, Orchestrator
from ystick.core.pipeline import STAGE_ORDER
from ystick.logging_conf import configure_logging
from ystick.state.models import AWAITING_APPROVAL, DONE, FAILED
from ystick.utils.ids import new_project_id


@dataclass
class BatchEntry:
    title: str
    minutes: int = 8
    short: bool = False
    mock: bool = False


@dataclass
class BatchResult:
    project_id: str
    title: str
    outcome: str          # "done" | "failed" | "awaiting_approval"
    error: str = ""
    stages_done: list[str] = field(default_factory=list)


def load_plan(path: Path) -> list[BatchEntry]:
    """Parse weekly_plan.yaml into a list of BatchEntry objects."""
    data = yaml.safe_load(path.read_text())
    entries = []
    for p in data.get("projects", []):
        entries.append(BatchEntry(
            title=p["title"],
            minutes=int(p.get("minutes", 8)),
            short=bool(p.get("short", False)),
            mock=bool(p.get("mock", False)),
        ))
    return entries


def _auto_approve_pending_gates(orch: Orchestrator, project_id: str) -> None:
    """Advance through any gates that fired during the last iter_run segment.
    topic_selection always picks index 0; all others just unblock."""
    for gate in GATE_AFTER_STAGE:
        if orch.store.get_approval(project_id, gate) is not None:
            continue
        stage_name = GATE_AFTER_STAGE[gate]
        state = orch.store.get_status(project_id, stage_name)
        if state.status != AWAITING_APPROVAL:
            continue
        decision = {"select": 0} if gate == "topic_selection" else {}
        orch.approve(project_id, gate, decision)


def run_entry(orch: Orchestrator, entry: BatchEntry) -> BatchResult:
    """Run one plan entry to completion, auto-approving every gate."""
    project_id = new_project_id(entry.title)
    log = configure_logging(project_id)
    orch.init_project(
        project_id,
        entry.title,
        target_minutes=entry.minutes,
        mock=entry.mock,
        generate_short=entry.short,
    )

    stages_done: list[str] = []
    # Loop: run → auto-approve any gate that fired → run again → repeat
    # until the pipeline either finishes or fails (no infinite loops: each
    # iteration must advance at least one stage or we're stuck).
    for _guard in range(len(STAGE_ORDER) + len(GATE_AFTER_STAGE) + 1):
        outcome = "done"
        for event in orch.iter_run(project_id, log=log):
            status = event.get("status")
            stage = event.get("stage")
            if status == "done" and stage:
                stages_done.append(stage)
            elif status == "failed":
                error = event.get("error", "")
                return BatchResult(project_id, entry.title, "failed", error=error, stages_done=stages_done)
            elif status == "awaiting_approval":
                outcome = "awaiting_approval"
                break
            elif status == "pipeline_done":
                outcome = "done"

        if outcome == "done":
            return BatchResult(project_id, entry.title, "done", stages_done=stages_done)

        # Gate fired — approve and loop back
        _auto_approve_pending_gates(orch, project_id)

    # Exceeded the guard limit — something is stuck
    return BatchResult(
        project_id, entry.title, "failed",
        error="batch guard limit exceeded — pipeline did not make progress",
        stages_done=stages_done,
    )


def run_plan(plan_path: Path, mock_override: bool | None = None) -> Iterator[tuple[BatchEntry, BatchResult]]:
    """Yield (entry, result) as each project in the plan completes.
    Caller can stream progress rather than waiting for the whole batch."""
    entries = load_plan(plan_path)
    orch = Orchestrator()
    for entry in entries:
        if mock_override is not None:
            entry = BatchEntry(entry.title, entry.minutes, entry.short, mock=mock_override)
        result = run_entry(orch, entry)
        yield entry, result
