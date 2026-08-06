"""Human-readable summaries of what's pending at each approval gate, used
by the CLI when a run stops with status='awaiting_approval'."""
from __future__ import annotations

from pathlib import Path

from ystick.core.pipeline import STAGE_FOLDERS
from ystick.utils.files import read_json

GATE_STAGE = {
    "topic_selection": "topic_discovery",
    "script_review": "script_generation",
    "storyboard_review": "scene_planning",
    "final_review": "canva_finishing",
}


def describe_pending(project_dir: Path, gate: str) -> str:
    folder = STAGE_FOLDERS[GATE_STAGE[gate]]
    stage_dir = project_dir / folder

    if gate == "topic_selection":
        ideas = read_json(stage_dir / "ideas.json")
        lines = [
            f"  [{i}] (score {idea['weighted_score']}) {idea['title']} — {idea['one_line_pitch']}"
            for i, idea in enumerate(ideas)
        ]
        return "Select a topic with --select N:\n" + "\n".join(lines)
    if gate == "script_review":
        return f"Review/edit the script at {stage_dir / 'script.md'}, then approve."
    if gate == "storyboard_review":
        storyboard = read_json(stage_dir / "storyboard.json")
        return f"Storyboard has {len(storyboard)} scenes — review {stage_dir / 'storyboard.json'}, then approve."
    if gate == "final_review":
        final_dir = project_dir / STAGE_FOLDERS["canva_finishing"]
        return f"Review the branded cut in {final_dir}, then approve to draft YouTube packaging."
    return "Review pending output, then approve."
