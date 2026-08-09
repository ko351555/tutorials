"""Build one final long-form video and (optionally) upload it — the
automated replacement for: Canva loop -> Clideo loop -> CapCut assemble ->
manual YouTube upload.

You still create the 10s silent clip in Google Flow and the music track in
Suno by hand (per your workflow), then hand this script the two downloaded
files plus the content file Claude generated for that video's title/
description/tags.

Example:
    python create_video.py \
        --content-file sample_content/dream_sanctum_videos_11_15.md \
        --video-number 11 \
        --clip ~/Downloads/video_11_clip.mp4 \
        --audio ~/Downloads/video_11_track.mp3 \
        --hours 8 \
        --output-dir ./output \
        --upload --privacy private
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Callable

sys.path.insert(0, str(Path(__file__).parent / "pipeline"))

from content_parser import get_video, VideoMetadata  # noqa: E402
from assemble import assemble  # noqa: E402


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "video"


def build_output_path(content_file: str, video_number: int, output_dir: str) -> tuple[VideoMetadata, Path]:
    meta: VideoMetadata = get_video(content_file, video_number)
    output_path = Path(output_dir) / f"video_{video_number}_{slugify(meta.video_name)}.mp4"
    return meta, output_path


def assemble_only(
    content_file: str,
    video_number: int,
    clip: str,
    audio: str,
    hours: float,
    output_dir: str = "output",
    reencode: bool = False,
    video_bitrate: str = "2500k",
    dry_run: bool = False,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[str, float], None] | None = None,
) -> dict:
    """Runs just the ffmpeg loop+mux stage. Returns enough to hand to
    upload_only() later (or to preview/inspect before deciding to upload).
    """
    meta, output_path = build_output_path(content_file, video_number, output_dir)

    assemble(
        video_path=clip,
        audio_path=audio,
        output_path=output_path,
        hours=hours,
        copy_video=not reencode,
        video_bitrate=video_bitrate,
        dry_run=dry_run,
        on_log=on_log,
        on_progress=(lambda pct: on_progress("assemble", pct)) if on_progress else None,
    )

    return {
        "video_number": video_number,
        "video_name": meta.video_name,
        "output_path": str(output_path),
    }


def upload_only(
    content_file: str,
    video_number: int,
    output_path: str,
    privacy: str = "private",
    publish_at: str | None = None,
    category_id: str = "10",
    thumbnail: str | None = None,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[str, float], None] | None = None,
) -> str:
    """Runs just the YouTube upload stage against an already-assembled file."""
    sys.path.insert(0, str(Path(__file__).parent / "pipeline"))
    from youtube_upload import upload_video

    meta: VideoMetadata = get_video(content_file, video_number)

    return upload_video(
        file_path=output_path,
        title=meta.youtube_title,
        description=meta.youtube_description,
        tags=meta.youtube_tags,
        category_id=category_id,
        privacy_status=privacy,
        publish_at=publish_at,
        thumbnail_path=thumbnail,
        on_log=on_log,
        on_progress=(lambda pct: on_progress("upload", pct)) if on_progress else None,
    )


def run_single(
    content_file: str,
    video_number: int,
    clip: str,
    audio: str,
    hours: float,
    output_dir: str = "output",
    reencode: bool = False,
    video_bitrate: str = "2500k",
    upload: bool = False,
    privacy: str = "private",
    publish_at: str | None = None,
    category_id: str = "10",
    thumbnail: str | None = None,
    dry_run: bool = False,
    on_log: Callable[[str], None] | None = None,
    on_progress: Callable[[str, float], None] | None = None,
) -> dict:
    """CLI/batch convenience: assemble then (if requested) upload, straight
    through with no pause in between. The web UI instead calls assemble_only()
    and upload_only() separately so it can gate the upload on user approval —
    see webui/app.py.

    `on_progress(phase, percent)` is called with phase "assemble" during
    ffmpeg looping/muxing and phase "upload" during the YouTube upload, each
    0-100, so a UI can track the two stages separately (or combine them).
    """
    log = on_log or print

    result = assemble_only(
        content_file, video_number, clip, audio, hours,
        output_dir=output_dir, reencode=reencode, video_bitrate=video_bitrate,
        dry_run=dry_run, on_log=log, on_progress=on_progress,
    )
    result["youtube_id"] = None

    if upload and not dry_run:
        result["youtube_id"] = upload_only(
            content_file, video_number, result["output_path"],
            privacy=privacy, publish_at=publish_at, category_id=category_id,
            thumbnail=thumbnail, on_log=log, on_progress=on_progress,
        )
    elif upload and dry_run:
        meta = get_video(content_file, video_number)
        log(f"[dry-run] Would upload '{meta.youtube_title}' with {len(meta.youtube_tags)} tags")

    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--content-file", required=True)
    ap.add_argument("--video-number", type=int, required=True)
    ap.add_argument("--clip", required=True, help="Silent short video clip from Google Flow")
    ap.add_argument("--audio", required=True, help="Music track downloaded from Suno")
    ap.add_argument("--hours", type=float, required=True)
    ap.add_argument("--output-dir", default="output")
    ap.add_argument("--reencode", action="store_true", help="See assemble.py --reencode")
    ap.add_argument("--video-bitrate", default="2500k")
    ap.add_argument("--upload", action="store_true")
    ap.add_argument("--privacy", default="private", choices=["private", "unlisted", "public"])
    ap.add_argument("--publish-at", default=None)
    ap.add_argument("--category-id", default="10")
    ap.add_argument("--thumbnail", default=None)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    result = run_single(
        content_file=args.content_file,
        video_number=args.video_number,
        clip=args.clip,
        audio=args.audio,
        hours=args.hours,
        output_dir=args.output_dir,
        reencode=args.reencode,
        video_bitrate=args.video_bitrate,
        upload=args.upload,
        privacy=args.privacy,
        publish_at=args.publish_at,
        category_id=args.category_id,
        thumbnail=args.thumbnail,
        dry_run=args.dry_run,
    )
    print(result)


if __name__ == "__main__":
    main()
