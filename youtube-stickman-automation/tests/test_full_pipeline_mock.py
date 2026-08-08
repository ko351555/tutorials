from pathlib import Path

from ystick.core.orchestrator import GATE_AFTER_STAGE, Orchestrator
from ystick.core.pipeline import STAGE_FOLDERS, STAGE_ORDER


def test_mock_run_passes_through_caption_burn_in_and_completes(tmp_path: Path):
    """End-to-end regression test for inserting the caption_burn_in stage
    between canva_finishing and youtube_packaging: the final_review gate
    now fires after caption_burn_in (not canva_finishing), and Packaging
    must read caption_burn_in's output, not canva_finishing's directly."""
    orch = Orchestrator(projects_root=tmp_path)
    project_id = "test-project"
    orch.init_project(project_id, "a test idea", mock=True)

    assert "caption_burn_in" in STAGE_ORDER
    assert STAGE_ORDER.index("canva_finishing") < STAGE_ORDER.index("caption_burn_in") < STAGE_ORDER.index("youtube_packaging")
    assert GATE_AFTER_STAGE["final_review"] == "caption_burn_in"

    # Drain every gate before final_review (topic_selection is enabled by
    # default in settings.yaml) so we actually reach caption_burn_in.
    for _ in range(len(GATE_AFTER_STAGE)):
        outcome = orch.run(project_id)
        if outcome != "awaiting_approval":
            break
        status = {s.stage: s for s in orch.status(project_id)}
        pending_gate = next(
            g for g, stage in GATE_AFTER_STAGE.items() if status[stage].status == "awaiting_approval"
        )
        if pending_gate == "final_review":
            break
        orch.approve(project_id, pending_gate, {})

    status = {s.stage: s for s in orch.status(project_id)}
    assert status["caption_burn_in"].status == "awaiting_approval"

    final_cut = orch.project_dir(project_id) / STAGE_FOLDERS["caption_burn_in"] / "final_cut.mp4"
    assert final_cut.exists()

    orch.approve(project_id, "final_review", {})
    outcome = orch.run(project_id)
    assert outcome == "done"

    packaging_path = orch.project_dir(project_id) / STAGE_FOLDERS["youtube_packaging"] / "packaging.json"
    assert packaging_path.exists()
