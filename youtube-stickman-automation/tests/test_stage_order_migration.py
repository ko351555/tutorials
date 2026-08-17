from pathlib import Path

from ystick.core.orchestrator import Orchestrator
from ystick.core.pipeline import STAGE_ORDER
from ystick.state.models import PENDING


def test_status_backfills_rows_for_stages_added_after_project_creation(tmp_path: Path):
    """Real production bug: a project created before caption_burn_in
    existed in STAGE_ORDER had no row for it in runs.db at all, so
    orch.status() silently omitted it from the returned list and the UI's
    status_by_stage[stage_name] lookup raised KeyError. ensure_project's
    INSERT OR IGNORE is idempotent, so status() (and iter_run()) can safely
    re-run it on every call to backfill any stage STAGE_ORDER has gained
    since the project's runs.db rows were first written."""
    orch = Orchestrator(projects_root=tmp_path)
    project_id = "old-project"

    # Simulate a project created under an older, shorter STAGE_ORDER —
    # every stage except the newest one.
    old_order = [s for s in STAGE_ORDER if s != "caption_burn_in"]
    orch.store.ensure_project(project_id, old_order)

    states = orch.status(project_id)
    stages_seen = {s.stage for s in states}
    assert "caption_burn_in" in stages_seen
    assert stages_seen == set(STAGE_ORDER)

    backfilled = next(s for s in states if s.stage == "caption_burn_in")
    assert backfilled.status == PENDING
