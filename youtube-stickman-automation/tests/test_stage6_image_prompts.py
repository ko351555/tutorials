from pathlib import Path

from ystick.config import Secrets, load_settings
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext
from ystick.stages.stage6_image_prompts import ImagePromptsStage
from ystick.utils.files import write_json


class _RecordingLLMClient:
    def __init__(self):
        self.calls = []

    def complete(self, prompt, *, system=None, json_mode=False, mock_key="generic"):
        self.calls.append(prompt)
        return f"[FAKE PROMPT for call {len(self.calls)}]"


def _make_ctx(project_dir: Path, llm, storyboard: list[dict]) -> ProjectContext:
    write_json(project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json", storyboard)
    settings = load_settings()
    return ProjectContext(
        project_id="image-prompts-test",
        project_dir=project_dir,
        settings=settings,
        secrets=Secrets(),
        mock=False,
        extra={"llm": llm},
    )


def test_prompt_includes_exact_narration_and_scene_position(tmp_path: Path):
    """Regression test for the "prompts don't sync with the audio"
    complaint: each scene's prompt-writing call must receive that scene's
    exact narration text (not a summary) plus its position in the video,
    so the LLM can key the visual off the specific line being narrated."""
    llm = _RecordingLLMClient()
    storyboard = [
        {"scene_id": "scene_001", "hold_previous_image": False, "narration_excerpt": "Not time. A feeling."},
        {"scene_id": "scene_002", "hold_previous_image": False, "narration_excerpt": "That changes everything."},
    ]
    ctx = _make_ctx(tmp_path, llm, storyboard)

    ImagePromptsStage().run(ctx)

    assert len(llm.calls) == 2
    assert '"Not time. A feeling."' in llm.calls[0]
    assert "scene 1 of 2" in llm.calls[0]
    assert '"That changes everything."' in llm.calls[1]
    assert "scene 2 of 2" in llm.calls[1]


def test_visual_blueprint_content_is_injected_verbatim(tmp_path: Path):
    llm = _RecordingLLMClient()
    storyboard = [{"scene_id": "scene_001", "hold_previous_image": False, "narration_excerpt": "hello"}]
    ctx = _make_ctx(tmp_path, llm, storyboard)

    ImagePromptsStage().run(ctx)

    # Key phrases from the filled-in config/visual_blueprint.md should be
    # present verbatim — i.e. the file is actually being read and
    # injected, not a stale/empty placeholder.
    assert "On-Image Text Captions" in llm.calls[0]
    assert "whiteboard-marker" in llm.calls[0].lower()


def test_held_scenes_are_not_sent_to_the_llm(tmp_path: Path):
    llm = _RecordingLLMClient()
    storyboard = [
        {"scene_id": "scene_001", "hold_previous_image": False, "narration_excerpt": "first"},
        {"scene_id": "scene_002", "hold_previous_image": True, "narration_excerpt": "still first idea"},
    ]
    ctx = _make_ctx(tmp_path, llm, storyboard)

    prompts_result = ImagePromptsStage().run(ctx)

    assert len(llm.calls) == 1
    assert prompts_result == {"num_prompts": 1, "num_reused": 1}
