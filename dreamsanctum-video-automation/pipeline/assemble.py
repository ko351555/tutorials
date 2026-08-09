"""Replace the Canva (loop video) + Clideo (loop audio) + CapCut (combine and
loop to full length) stage of the manual workflow with a single ffmpeg pass.

Why one pass instead of three: Canva/Clideo/CapCut each have export-length
limits, which is the only reason the manual process builds a 15-minute video
loop and a 30-minute audio loop before assembling the final 5-8 hour file.
ffmpeg has no such limit, so the silent video clip and the music clip can
each be looped directly to the full target duration and muxed in one
command. The perceptual repeat period is identical either way (still the
length of the source clip) — the multi-stage build added no smoothness, only
extra re-encoding generation loss.

Usage:
    python assemble.py \
        --video clip.mp4 --audio track.mp3 \
        --hours 8 --output final/video_11.mp4

    # See the ffmpeg command without running it:
    python assemble.py --video clip.mp4 --audio track.mp3 --hours 8 \
        --output final/video_11.mp4 --dry-run
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")


class FfmpegNotFound(RuntimeError):
    pass


def _require_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise FfmpegNotFound(
            "ffmpeg was not found on PATH. Install it first:\n"
            "  macOS:   brew install ffmpeg\n"
            "  Ubuntu:  sudo apt install ffmpeg\n"
            "  Windows: https://ffmpeg.org/download.html"
        )


def probe_duration_seconds(path: str | Path) -> float:
    """Return the duration of a media file in seconds using ffprobe."""
    if shutil.which("ffprobe") is None:
        raise FfmpegNotFound("ffprobe was not found on PATH (installed alongside ffmpeg).")
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(out.stdout)["format"]["duration"])


def build_ffmpeg_command(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    target_seconds: float,
    copy_video: bool = True,
    video_bitrate: str | None = "2500k",
    audio_bitrate: str = "192k",
    fade_seconds: float = 15.0,
) -> list[str]:
    """Build the ffmpeg argv that loops video+audio independently to
    target_seconds and muxes them into one file, with a fade-in/out on the
    audio at the very start/end of the whole video (not at every loop seam).
    """
    fade_out_start = max(target_seconds - fade_seconds, 0)

    audio_filter = (
        f"afade=t=in:st=0:d={fade_seconds},"
        f"afade=t=out:st={fade_out_start}:d={fade_seconds}"
    )

    cmd = [
        "ffmpeg", "-y",
        "-stream_loop", "-1", "-i", str(video_path),
        "-stream_loop", "-1", "-i", str(audio_path),
        "-t", f"{target_seconds:.3f}",
        "-map", "0:v:0", "-map", "1:a:0",
        "-af", audio_filter,
        "-c:a", "aac", "-b:a", audio_bitrate,
    ]

    if copy_video:
        cmd += ["-c:v", "copy"]
    else:
        cmd += ["-c:v", "libx264", "-preset", "veryfast"]
        if video_bitrate:
            cmd += ["-b:v", video_bitrate, "-maxrate", video_bitrate, "-bufsize", "2M"]
        else:
            cmd += ["-crf", "23"]

    cmd += ["-movflags", "+faststart", str(output_path)]
    return cmd


def assemble(
    video_path: str | Path,
    audio_path: str | Path,
    output_path: str | Path,
    hours: float,
    copy_video: bool = True,
    video_bitrate: str | None = "2500k",
    dry_run: bool = False,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[float], None] | None = None,
) -> Path:
    """Run ffmpeg to build the final looped+muxed video.

    `on_log(message)` receives human-readable status lines (defaults to
    print). `on_progress(percent)` receives 0-100 float updates parsed from
    ffmpeg's own `time=` output, for a UI progress bar; it is not called at
    all if omitted, and log lines are throttled to roughly every 5% so a
    long 8-hour encode doesn't flood the log with hundreds of lines.
    """
    log = on_log or print
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    target_seconds = hours * 3600

    cmd = build_ffmpeg_command(
        video_path, audio_path, output_path, target_seconds,
        copy_video=copy_video, video_bitrate=video_bitrate,
    )

    if dry_run:
        log(" ".join(cmd))
        return output_path

    _require_ffmpeg()
    log(f"Assembling {hours}h video -> {output_path}")
    log(f"  video source: {video_path}")
    log(f"  audio source: {audio_path}")

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
    )
    last_logged_bucket = -1
    for line in process.stdout:
        m = TIME_RE.search(line)
        if not m:
            continue
        h, mnt, s = m.groups()
        current_seconds = int(h) * 3600 + int(mnt) * 60 + float(s)
        pct = min(current_seconds / target_seconds * 100, 100.0) if target_seconds else 100.0

        if on_progress:
            on_progress(pct)

        bucket = int(pct // 5)
        if bucket != last_logged_bucket:
            last_logged_bucket = bucket
            log(f"  ffmpeg progress: {pct:.0f}%")

    process.wait()
    if process.returncode != 0:
        raise subprocess.CalledProcessError(process.returncode, cmd)

    if on_progress:
        on_progress(100.0)
    log(f"Done: {output_path}")
    return output_path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--video", required=True, help="Silent short video clip (from Google Flow)")
    ap.add_argument("--audio", required=True, help="Short music clip (downloaded from Suno)")
    ap.add_argument("--output", required=True, help="Path for the final long-form MP4")
    ap.add_argument("--hours", type=float, required=True, help="Target total duration, e.g. 8 or 5")
    ap.add_argument(
        "--reencode", action="store_true",
        help="Re-encode video with libx264 instead of stream-copying the looped source. "
             "Stream copy is fast and lossless but the output file size scales linearly with "
             "how many times the clip repeats (a 10s clip looped for 8h can be tens of GB). "
             "Re-encoding at --video-bitrate keeps the file YouTube-upload-friendly.",
    )
    ap.add_argument("--video-bitrate", default="2500k", help="Target video bitrate when --reencode is set (default 2500k)")
    ap.add_argument("--dry-run", action="store_true", help="Print the ffmpeg command instead of running it")
    args = ap.parse_args()

    assemble(
        args.video, args.audio, args.output, args.hours,
        copy_video=not args.reencode,
        video_bitrate=args.video_bitrate,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
