from pathlib import Path

import pytest

from ystick.config import Secrets
from ystick.core.exceptions import FatalError
from ystick.core.pipeline import ProjectContext
from ystick.stages import stage7_image_generation as stage7_module
from ystick.stages.stage7_image_generation import ImageGenerationStage
from ystick.utils.files import read_json, write_json


class _FailOnNthClient:
    """Fake ImageGenClient: succeeds on the first `fail_at - 1` calls, then
    raises FatalError — simulating scene N failing (quota, refusal, etc.)
    partway through a multi-scene run."""

    def __init__(self, secrets, mock=False, fail_at=3):
        self.fail_at = fail_at
        self.calls = 0

    def generate(self, prompt, out_path, reference_image=None):
        self.calls += 1
        if self.calls >= self.fail_at:
            raise FatalError(f"simulated failure on call {self.calls}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_bytes(b"FAKE_IMAGE")
        return out_path


def _make_ctx(project_dir: Path, num_scenes: int) -> ProjectContext:
    write_json(
        project_dir / "06_prompts" / "image_prompts.json",
        [{"scene_id": f"scene_{i:03d}", "prompt": f"prompt {i}"} for i in range(1, num_scenes + 1)],
    )
    return ProjectContext(
        project_id="checkpoint-test",
        project_dir=project_dir,
        settings=None,
        secrets=Secrets(image_gen_provider="openai", image_gen_api_key="fake"),
        mock=False,
        extra={},
    )


def test_manifest_checkpoints_per_scene_so_a_later_failure_doesnt_lose_earlier_progress(
    tmp_path: Path, monkeypatch
):
    """Real production risk: if manifest.json were only written once at the
    end of the stage, a scene N failure would mean scenes 1..N-1 (already
    successfully generated and paid for) get silently re-generated — and
    re-billed — on the next retry, because the cache-hit check reads
    manifest.json from disk. It must be written incrementally."""
    fake_client = _FailOnNthClient(None, fail_at=3)
    monkeypatch.setattr(stage7_module, "ImageGenClient", lambda secrets, mock=False: fake_client)

    ctx = _make_ctx(tmp_path, num_scenes=4)

    with pytest.raises(FatalError, match="simulated failure"):
        ImageGenerationStage().run(ctx)

    manifest = read_json(tmp_path / "07_images" / "manifest.json")
    assert "scene_001" in manifest
    assert "scene_002" in manifest
    assert "scene_003" not in manifest
    assert fake_client.calls == 3


def test_resuming_after_a_partial_failure_skips_already_generated_scenes(tmp_path: Path, monkeypatch):
    fake_client = _FailOnNthClient(None, fail_at=3)
    monkeypatch.setattr(stage7_module, "ImageGenClient", lambda secrets, mock=False: fake_client)
    ctx = _make_ctx(tmp_path, num_scenes=4)

    with pytest.raises(FatalError):
        ImageGenerationStage().run(ctx)
    assert fake_client.calls == 3

    # Resume: raise fail_at past the end so the retry succeeds all the way
    # through — the already-generated scenes 1-2 must NOT trigger new
    # generate() calls (they were cached, not re-billed).
    fake_client.fail_at = 999
    fake_client.calls = 0
    result = ImageGenerationStage().run(ctx)

    assert fake_client.calls == 2  # only scene_003 and scene_004 were still needed
    assert result["cached"] == 2
    assert result["generated"] == 2
