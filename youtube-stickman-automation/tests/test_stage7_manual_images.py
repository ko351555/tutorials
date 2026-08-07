from pathlib import Path

import pytest

from ystick.config import Secrets
from ystick.core.exceptions import FatalError
from ystick.core.pipeline import ProjectContext
from ystick.stages.stage7_image_generation import ImageGenerationStage, find_uploaded_image
from ystick.utils.files import read_json, write_json


def _make_ctx(project_dir: Path) -> ProjectContext:
    write_json(
        project_dir / "06_prompts" / "image_prompts.json",
        [
            {"scene_id": "scene_001", "prompt": "a stickman waving hello"},
            {"scene_id": "scene_002", "prompt": "a stickman holding a coin"},
            {"scene_id": "scene_003", "reuse_scene": "scene_001"},
        ],
    )
    return ProjectContext(
        project_id="manual-image-test",
        project_dir=project_dir,
        settings=None,
        secrets=Secrets(image_gen_provider="manual"),
        mock=False,
        extra={},
    )


def test_missing_uploads_reports_only_scenes_needing_direct_upload(tmp_path: Path):
    ctx = _make_ctx(tmp_path)
    with pytest.raises(FatalError) as exc_info:
        ImageGenerationStage().run(ctx)
    msg = str(exc_info.value)
    assert "scene_001" in msg
    assert "scene_002" in msg
    # scene_003 only reuses scene_001 — it shouldn't be reported as a
    # separate thing needing its own upload.
    assert "scene_003" not in msg


def test_succeeds_once_images_are_placed_including_reuse_copy(tmp_path: Path):
    ctx = _make_ctx(tmp_path)
    images_dir = tmp_path / "07_images"
    (images_dir / "scene_001").mkdir(parents=True)
    (images_dir / "scene_002").mkdir(parents=True)
    (images_dir / "scene_001" / "image.png").write_bytes(b"\x89PNG\r\n\x1a\nFAKE1")
    (images_dir / "scene_002" / "image.jpg").write_bytes(b"\xff\xd8\xffFAKE2")

    summary = ImageGenerationStage().run(ctx)

    assert summary == {"generated": 0, "cached": 0, "reused": 1, "uploaded": 2}
    manifest = read_json(images_dir / "manifest.json")
    assert manifest["scene_001"]["path"].endswith("image.png")
    assert manifest["scene_002"]["path"].endswith("image.jpg")
    assert manifest["scene_003"]["path"].endswith("image.png")
    assert Path(manifest["scene_003"]["path"]).exists()


def test_find_uploaded_image_checks_all_supported_extensions(tmp_path: Path):
    scene_dir = tmp_path / "scene_001"
    scene_dir.mkdir()
    assert find_uploaded_image(scene_dir) is None
    (scene_dir / "image.webp").write_bytes(b"fake")
    assert find_uploaded_image(scene_dir) == scene_dir / "image.webp"
