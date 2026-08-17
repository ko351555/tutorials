"""Stage 8: deterministic FFmpeg assembly — the reliable, scriptable
backbone (see docs/ARCHITECTURE.md §6) vs. Google Flow, which has no API
and is treated as an optional manual enhancement spliced in via
`hero_clips_dir` before this runs.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import structlog

from ystick.core.exceptions import FatalError

log = structlog.get_logger()


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def _subtitles_filter_available() -> bool:
    """Some ffmpeg builds (notably a handful of Homebrew installs observed
    in the wild) ship without libass, so the `subtitles` filter isn't
    compiled in at all — ffmpeg then fails with "No such filter:
    'subtitles'" no matter how the argument is written. Check up front so
    Assembly can degrade to a silent-of-captions video instead of failing
    the whole stage over what's an enhancement, not the deliverable."""
    try:
        result = subprocess.run(
            ["ffmpeg", "-hide_banner", "-filters"], capture_output=True, check=True
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        return False
    return b" subtitles " in result.stdout


def run_ffmpeg(cmd: list[str]) -> None:
    """Runs an ffmpeg command, raising FatalError with the actual decoded
    stderr on failure — ffmpeg's own error output is where the real reason
    lives (bad filter syntax, unsupported codec, corrupt input, missing
    libass, etc.); a bare CalledProcessError repr hides all of that."""
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except FileNotFoundError as exc:
        raise FatalError("ffmpeg not found on PATH — install it (e.g. `brew install ffmpeg`)") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode(errors="replace") if exc.stderr else "(no stderr captured)"
        raise FatalError(
            f"ffmpeg exited {exc.returncode}\ncommand: {' '.join(cmd)}\n\n{stderr[-3000:]}"
        ) from exc


def trim_audio(src_path: Path, start_ms: int, end_ms: int, out_path: Path, *, mock: bool = False) -> Path:
    """Cuts [start_ms, end_ms) out of src_path — used by Shorts creation to
    pull a standalone clip's narration out of the full-length audio without
    a second voice-generation API call."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if mock or not _ffmpeg_available():
        out_path.write_bytes(b"MOCK_MP3_PLACEHOLDER")
        return out_path
    # -ss before -i seeks the demuxer directly (fast, and accurate for
    # re-encoded output) rather than decoding-and-discarding up to the cut
    # point.
    run_ffmpeg([
        "ffmpeg", "-y", "-ss", str(start_ms / 1000), "-i", str(src_path),
        "-t", str((end_ms - start_ms) / 1000), "-c:a", "libmp3lame", str(out_path),
    ])
    return out_path


def _subtitles_vf_arg(srt_path: Path) -> str | None:
    """Builds the -vf value to burn `srt_path` in, or None if it can't/
    shouldn't be burned in (missing file, or the filter isn't compiled into
    this ffmpeg build) — callers should skip -vf entirely in that case
    rather than fail the stage over what's an enhancement, not the
    deliverable."""
    if not srt_path.exists():
        return None
    if not _subtitles_filter_available():
        log.warning(
            "assembly.subtitles_filter_unavailable",
            detail="ffmpeg build has no libass/subtitles filter — burning in "
            "captions skipped; reinstall ffmpeg with libass support to enable it "
            "(e.g. `brew reinstall ffmpeg`)",
        )
        return None
    # ffmpeg's filter-option parser splits the value on ':' to look for
    # further key=value pairs; a bare path with no colons never trips that
    # split, so the positional/shorthand mapping to `filename` doesn't kick
    # in either and the whole thing is rejected with "No option name near
    # ...". Naming the option explicitly and single-quoting the value
    # sidesteps that as well as the classic Windows-drive-letter colon issue
    # (C:\...) in one move; a literal single quote or backslash inside the
    # path is escaped so the quoting itself can't be broken out of.
    escaped_srt = str(srt_path).replace("\\", "\\\\").replace(":", "\\:").replace("'", "'\\''")
    return f"subtitles=filename='{escaped_srt}'"


def burn_captions(video_path: Path, srt_path: Path, out_path: Path, *, mock: bool = False) -> Path:
    """Burns srt_path's captions into video_path, writing out_path. Passes
    the video through unchanged (just copied) if captions can't be burned
    in for any reason (mock mode, no ffmpeg, no subtitles filter, missing/
    empty SRT) — this is an enhancement pass over an already-finished
    video, not something worth failing the pipeline over."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if mock or not _ffmpeg_available():
        shutil.copyfile(video_path, out_path)
        return out_path

    vf = _subtitles_vf_arg(srt_path)
    if vf is None:
        shutil.copyfile(video_path, out_path)
        return out_path

    run_ffmpeg(["ffmpeg", "-y", "-i", str(video_path), "-vf", vf, "-c:a", "copy", str(out_path)])
    return out_path


def _ms_to_srt_ts(ms: int) -> str:
    h, rem = divmod(ms, 3_600_000)
    m, rem = divmod(rem, 60_000)
    s, ms = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def write_srt(sentences: list[dict], out_path: Path) -> Path:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for i, sent in enumerate(sentences, start=1):
        lines.append(str(i))
        lines.append(f"{_ms_to_srt_ts(sent['start_ms'])} --> {_ms_to_srt_ts(sent['end_ms'])}")
        lines.append(sent["text"])
        lines.append("")
    out_path.write_text("\n".join(lines))
    return out_path


def build_video(
    scenes: list[dict],
    narration_path: Path,
    srt_path: Path,
    out_path: Path,
    *,
    fps: int = 30,
    resolution: str = "1920x1080",
    ken_burns: bool = True,
    subtitles: bool = True,
    hero_clips_dir: Path | None = None,
    mock: bool = False,
) -> Path:
    """scenes: [{"scene_id", "image_path", "duration_ms"}], in order.
    Any scene whose id has a matching file in hero_clips_dir (named
    "<scene_id>.mp4") uses that clip instead of the still image."""
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if mock or not _ffmpeg_available():
        out_path.write_bytes(b"MOCK_MP4_PLACEHOLDER")
        return out_path

    concat_list = out_path.parent / "concat_list.txt"
    width, height = resolution.split("x")
    per_clip_dir = out_path.parent / "clips"
    per_clip_dir.mkdir(exist_ok=True)

    clip_paths = []
    for scene in scenes:
        hero_clip = None
        if hero_clips_dir and hero_clips_dir.exists():
            candidate = hero_clips_dir / f"{scene['scene_id']}.mp4"
            if candidate.exists():
                hero_clip = candidate

        clip_out = per_clip_dir / f"{scene['scene_id']}.mp4"
        duration_s = max(scene["duration_ms"] / 1000, 0.1)

        if hero_clip is not None:
            clip_paths.append(hero_clip)
            continue

        vf = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2"
        if ken_burns:
            zoom_frames = max(1, int(duration_s * fps))
            vf += (
                f",zoompan=z='min(zoom+0.0008,1.15)':d={zoom_frames}:"
                f"s={width}x{height}:fps={fps}"
            )
        cmd = [
            "ffmpeg", "-y", "-loop", "1", "-i", str(scene["image_path"]),
            "-t", str(duration_s), "-vf", vf, "-r", str(fps), str(clip_out),
        ]
        run_ffmpeg(cmd)
        clip_paths.append(clip_out)

    concat_list.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths))

    silent_video = out_path.parent / "silent_concat.mp4"
    run_ffmpeg(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(silent_video)]
    )

    vf_final = _subtitles_vf_arg(srt_path) if subtitles else None

    cmd = ["ffmpeg", "-y", "-i", str(silent_video), "-i", str(narration_path)]
    if vf_final:
        cmd += ["-vf", vf_final]
    cmd += ["-c:v", "libx264", "-c:a", "aac", "-shortest", str(out_path)]
    run_ffmpeg(cmd)
    return out_path
