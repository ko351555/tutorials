import json
from pathlib import Path

from ystick.config import AttrDict, Secrets, load_settings
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext
from ystick.stages.stage9c_shorts_creation import (
    ShortsCreationStage,
    _select_window,
    _slice_scenes,
    _slice_sentences,
)
from ystick.utils.files import write_json


class _StubLLMClient:
    def __init__(self, response):
        self.response = response

    def complete(self, prompt, *, system=None, json_mode=False, mock_key="generic"):
        return json.dumps(self.response) if isinstance(self.response, dict) else self.response


def _sentence(text, start_ms, end_ms):
    return {"text": text, "start_ms": start_ms, "end_ms": end_ms}


# -- _select_window -----------------------------------------------------------

def test_select_window_accepts_a_valid_llm_pick():
    ctx = ProjectContext(
        project_id="t", project_dir=Path("/tmp"), settings=None, secrets=Secrets(),
        extra={"llm": _StubLLMClient({"start_ms": 5000, "end_ms": 50000, "reason": "hook"})},
    )
    sentences = [_sentence("a", 0, 5000), _sentence("b", 5000, 50000), _sentence("c", 50000, 60000)]
    start, end = _select_window(ctx, "full script", sentences, min_s=40, max_s=50)
    assert (start, end) == (5000, 50000)


def test_select_window_falls_back_when_llm_picks_out_of_range():
    ctx = ProjectContext(
        project_id="t", project_dir=Path("/tmp"), settings=None, secrets=Secrets(),
        extra={"llm": _StubLLMClient({"start_ms": 0, "end_ms": 999_999_999, "reason": "bad"})},
    )
    sentences = [_sentence("a", 0, 10000), _sentence("b", 10000, 20000)]
    start, end = _select_window(ctx, "full script", sentences, min_s=40, max_s=50)
    assert start == 0
    assert end == 20000  # clamped to total narration length, not the LLM's bogus value


def test_select_window_falls_back_when_llm_response_is_unparseable():
    ctx = ProjectContext(
        project_id="t", project_dir=Path("/tmp"), settings=None, secrets=Secrets(),
        extra={"llm": _StubLLMClient("not json at all")},
    )
    sentences = [_sentence("a", 0, 15000)]
    start, end = _select_window(ctx, "full script", sentences, min_s=40, max_s=50)
    assert (start, end) == (0, 15000)


def test_select_window_falls_back_when_duration_is_wildly_too_short():
    ctx = ProjectContext(
        project_id="t", project_dir=Path("/tmp"), settings=None, secrets=Secrets(),
        extra={"llm": _StubLLMClient({"start_ms": 0, "end_ms": 2000, "reason": "too short"})},
    )
    sentences = [_sentence("a", 0, 100000)]
    start, end = _select_window(ctx, "full script", sentences, min_s=40, max_s=50)
    assert (start, end) == (0, 50000)  # fallback, not the 2s pick


# -- _slice_scenes / _slice_sentences ------------------------------------------

def test_slice_scenes_keeps_only_overlapping_scenes_and_shifts_nothing_yet():
    storyboard = [
        {"scene_id": "scene_001", "start_ms": 0, "end_ms": 5000},
        {"scene_id": "scene_002", "start_ms": 5000, "end_ms": 15000},
        {"scene_id": "scene_003", "start_ms": 15000, "end_ms": 25000},
    ]
    manifest = {
        "scene_001": {"path": "/img/1.png"},
        "scene_002": {"path": "/img/2.png"},
        "scene_003": {"path": "/img/3.png"},
    }
    scenes = _slice_scenes(storyboard, manifest, start_ms=3000, end_ms=20000)
    ids = [s["scene_id"] for s in scenes]
    assert ids == ["scene_001", "scene_002", "scene_003"]
    assert scenes[0]["duration_ms"] == 2000  # 3000..5000
    assert scenes[1]["duration_ms"] == 10000  # 5000..15000
    assert scenes[2]["duration_ms"] == 5000  # 15000..20000


def test_slice_sentences_shifts_timestamps_relative_to_window_start():
    sentences = [_sentence("a", 0, 3000), _sentence("b", 3000, 8000), _sentence("c", 8000, 12000)]
    sliced = _slice_sentences(sentences, start_ms=2000, end_ms=10000)
    assert sliced[0] == {"text": "a", "start_ms": 0, "end_ms": 1000}
    assert sliced[1] == {"text": "b", "start_ms": 1000, "end_ms": 6000}
    assert sliced[2] == {"text": "c", "start_ms": 6000, "end_ms": 8000}


# -- full stage, mock mode -----------------------------------------------------

def _make_ctx(project_dir: Path) -> ProjectContext:
    write_json(
        project_dir / STAGE_FOLDERS["script_generation"] / "script.json",
        {"text": "A. B. C. D.", "chosen_idea": {"title": "Test Video Title"}},
    )
    write_json(
        project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json",
        [
            {"scene_id": "scene_001", "start_ms": 0, "end_ms": 4000, "duration_ms": 4000},
            {"scene_id": "scene_002", "start_ms": 4000, "end_ms": 8000, "duration_ms": 4000},
        ],
    )
    write_json(
        project_dir / STAGE_FOLDERS["timestamps"] / "transcript.json",
        {"sentences": [_sentence("A B", 0, 4000), _sentence("C D", 4000, 8000)]},
    )
    manifest_dir = project_dir / STAGE_FOLDERS["image_generation"]
    (manifest_dir / "scene_001").mkdir(parents=True, exist_ok=True)
    (manifest_dir / "scene_001" / "image.png").write_bytes(b"fake")
    (manifest_dir / "scene_002").mkdir(parents=True, exist_ok=True)
    (manifest_dir / "scene_002" / "image.png").write_bytes(b"fake")
    write_json(
        manifest_dir / "manifest.json",
        {
            "scene_001": {"path": str(manifest_dir / "scene_001" / "image.png")},
            "scene_002": {"path": str(manifest_dir / "scene_002" / "image.png")},
        },
    )
    (project_dir / STAGE_FOLDERS["voice_generation"]).mkdir(parents=True, exist_ok=True)
    (project_dir / STAGE_FOLDERS["voice_generation"] / "narration.mp3").write_bytes(b"MOCK_MP3_PLACEHOLDER")

    settings = load_settings()
    return ProjectContext(
        project_id="shorts-test",
        project_dir=project_dir,
        settings=settings,
        secrets=Secrets(),
        mock=True,
        extra={
            "llm": _StubLLMClient({"start_ms": 0, "end_ms": 8000, "reason": "whole thing"}),
            "blueprint": AttrDict({"name": "Test Channel"}),
        },
    )


def test_shorts_stage_produces_a_vertical_video_in_mock_mode(tmp_path: Path):
    ctx = _make_ctx(tmp_path)
    result = ShortsCreationStage().run(ctx)

    out_path = tmp_path / STAGE_FOLDERS["shorts_creation"] / "shorts_cut.mp4"
    assert out_path.exists()
    assert result["num_scenes"] == 2
    assert result["duration_s"] == 8.0


def test_shorts_stage_skips_when_disabled(tmp_path: Path):
    ctx = _make_ctx(tmp_path)
    # AttrDict wraps nested plain dicts fresh on every attribute access
    # (see config.AttrDict._wrap), so `ctx.settings.stages.x.attr = ...`
    # mutates a throwaway copy — bracket access on the real underlying
    # dict is what actually persists the change.
    ctx.settings["stages"]["shorts_creation"]["enabled"] = False

    result = ShortsCreationStage().run(ctx)

    assert result == {"skipped": True}
    assert not (tmp_path / STAGE_FOLDERS["shorts_creation"] / "shorts_cut.mp4").exists()
