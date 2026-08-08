import subprocess
from pathlib import Path

import pytest

from ystick.core.exceptions import FatalError
from ystick.integrations import video_assembly as va_module
from ystick.integrations.video_assembly import run_ffmpeg


def test_run_ffmpeg_surfaces_real_stderr(monkeypatch):
    def fake_run(cmd, check, capture_output):
        raise subprocess.CalledProcessError(
            234, cmd, output=b"", stderr=b"Unknown encoder 'libx264'\nsome more detail\n"
        )

    monkeypatch.setattr(va_module.subprocess, "run", fake_run)

    with pytest.raises(FatalError) as exc_info:
        run_ffmpeg(["ffmpeg", "-i", "in.mp4", "out.mp4"])

    msg = str(exc_info.value)
    assert "ffmpeg exited 234" in msg
    assert "Unknown encoder 'libx264'" in msg
    assert "ffmpeg -i in.mp4 out.mp4" in msg


def test_run_ffmpeg_missing_binary(monkeypatch):
    def fake_run(cmd, check, capture_output):
        raise FileNotFoundError()

    monkeypatch.setattr(va_module.subprocess, "run", fake_run)

    with pytest.raises(FatalError, match="ffmpeg not found on PATH"):
        run_ffmpeg(["ffmpeg", "-version"])


def test_run_ffmpeg_success_does_not_raise(monkeypatch):
    monkeypatch.setattr(va_module.subprocess, "run", lambda cmd, check, capture_output: None)
    run_ffmpeg(["ffmpeg", "-version"])


def test_build_video_subtitles_filter_uses_named_quoted_filename(tmp_path: Path, monkeypatch):
    """Regression test for a real production failure: ffmpeg's filter-option
    parser rejects a bare `subtitles=/some/path.srt` value when the path has
    no colons (it never finds a ':' to split on, so the positional shorthand
    mapping to `filename` never kicks in, and it errors "No option name
    near ..."). The fix names the option and single-quotes the value; this
    locks that exact -vf shape in place."""
    monkeypatch.setattr(va_module, "_ffmpeg_available", lambda: True)

    captured_cmds = []

    def fake_run_ffmpeg(cmd):
        captured_cmds.append(cmd)
        # Each ffmpeg call is expected to produce the file the next step reads.
        Path(cmd[-1]).parent.mkdir(parents=True, exist_ok=True)
        Path(cmd[-1]).write_bytes(b"fake")

    monkeypatch.setattr(va_module, "run_ffmpeg", fake_run_ffmpeg)

    scenes = [{"scene_id": "scene_001", "image_path": tmp_path / "img.png", "duration_ms": 1000}]
    narration = tmp_path / "narration.mp3"
    narration.write_bytes(b"fake")
    srt_path = tmp_path / "narration.srt"
    srt_path.write_text("1\n00:00:00,000 --> 00:00:01,000\nhello\n")
    out_path = tmp_path / "out" / "final.mp4"

    va_module.build_video(scenes, narration, srt_path, out_path, mock=False)

    final_cmd = captured_cmds[-1]
    vf_index = final_cmd.index("-vf")
    vf_value = final_cmd[vf_index + 1]
    assert vf_value == f"subtitles=filename='{srt_path}'"


def test_build_video_falls_back_to_mock_placeholder_without_ffmpeg(tmp_path: Path, monkeypatch):
    """When ffmpeg isn't on PATH, build_video degrades to a placeholder file
    instead of raising — this is the mock/CI-friendly fallback, distinct
    from a real ffmpeg failure (which raises FatalError via run_ffmpeg)."""
    monkeypatch.setattr(va_module, "_ffmpeg_available", lambda: False)

    scenes = [{"scene_id": "scene_001", "image_path": tmp_path / "img.png", "duration_ms": 1000}]
    out_path = tmp_path / "out" / "final.mp4"

    result = va_module.build_video(
        scenes, tmp_path / "narration.mp3", tmp_path / "narration.srt", out_path, mock=False
    )

    assert result == out_path
    assert out_path.read_bytes() == b"MOCK_MP4_PLACEHOLDER"
