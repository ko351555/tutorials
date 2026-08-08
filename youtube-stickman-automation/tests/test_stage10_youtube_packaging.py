import json
from pathlib import Path

from ystick.config import Secrets, load_blueprint, load_settings
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext
from ystick.stages.stage10_youtube_packaging import YoutubePackagingStage
from ystick.utils.files import write_json


class _StubLLMClient:
    def __init__(self, response: dict):
        self.response = response
        self.calls = []

    def complete(self, prompt, *, system=None, json_mode=False, mock_key="generic"):
        self.calls.append({"prompt": prompt, "system": system})
        return json.dumps(self.response)


def _make_ctx(project_dir: Path, llm) -> ProjectContext:
    settings = load_settings()
    blueprint = load_blueprint(settings)

    script_dir = project_dir / STAGE_FOLDERS["script_generation"]
    write_json(
        script_dir / "script.json",
        {"chosen_idea": {"title": "5 AI Jobs Test Video"}, "text": "Some narration text " * 20},
    )
    storyboard_dir = project_dir / STAGE_FOLDERS["scene_planning"]
    write_json(storyboard_dir / "storyboard.json", [{"scene_id": "scene_001"}])

    return ProjectContext(
        project_id="packaging-test",
        project_dir=project_dir,
        settings=settings,
        secrets=Secrets(),
        mock=True,
        extra={"llm": llm, "blueprint": blueprint},
    )


def test_tags_backfilled_when_llm_omits_them(tmp_path: Path):
    """Real production complaint: the packaging output sometimes had no
    tags to copy into YouTube Studio. Whatever the LLM does, the stage
    itself must never leave tags empty."""
    llm = _StubLLMClient({
        "title": "t", "description": "d", "tags": [], "thumbnail_text": "T",
        "chapters": [], "pinned_comment": "", "community_post": "",
        "shorts_title": "", "shorts_description": "",
    })
    ctx = _make_ctx(tmp_path, llm)

    YoutubePackagingStage().run(ctx)

    packaging = json.loads((tmp_path / STAGE_FOLDERS["youtube_packaging"] / "packaging.json").read_text())
    assert packaging["tags"]
    assert isinstance(packaging["tags"], list)


def test_thumbnail_prompts_backfilled_when_llm_omits_them(tmp_path: Path):
    """Real production request: 5 copyable thumbnail image-gen prompts.
    If the LLM doesn't return them, the stage must still produce 5."""
    llm = _StubLLMClient({
        "title": "t", "description": "d", "tags": ["a", "b"], "thumbnail_text": "T",
        "chapters": [], "pinned_comment": "", "community_post": "",
        "shorts_title": "", "shorts_description": "",
    })
    ctx = _make_ctx(tmp_path, llm)

    YoutubePackagingStage().run(ctx)

    packaging = json.loads((tmp_path / STAGE_FOLDERS["youtube_packaging"] / "packaging.json").read_text())
    assert len(packaging["thumbnail_prompts"]) == 5
    assert all(isinstance(p, str) and p for p in packaging["thumbnail_prompts"])


def test_llm_provided_tags_and_thumbnail_prompts_pass_through_untouched(tmp_path: Path):
    llm = _StubLLMClient({
        "title": "t", "description": "d", "tags": ["real", "tags", "here"],
        "thumbnail_text": "T", "thumbnail_prompts": ["p1", "p2", "p3", "p4", "p5"],
        "chapters": [], "pinned_comment": "", "community_post": "",
        "shorts_title": "", "shorts_description": "",
    })
    ctx = _make_ctx(tmp_path, llm)

    YoutubePackagingStage().run(ctx)

    packaging = json.loads((tmp_path / STAGE_FOLDERS["youtube_packaging"] / "packaging.json").read_text())
    assert packaging["tags"] == ["real", "tags", "here"]
    assert packaging["thumbnail_prompts"] == ["p1", "p2", "p3", "p4", "p5"]
