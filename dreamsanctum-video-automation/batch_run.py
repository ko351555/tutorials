"""Process a whole batch of videos (your usual "10 videos in a file" run)
from one YAML config: loop clip -> loop audio -> mux -> upload, for every
video entry, continuing past individual failures and printing a summary at
the end.

Usage:
    cp batch_config.example.yaml batch_config.yaml   # then edit paths
    python batch_run.py batch_config.yaml
    python batch_run.py batch_config.yaml --dry-run   # print ffmpeg commands, skip upload
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

from create_video import run_single


def compute_publish_at(schedule: dict | None, index: int) -> str | None:
    if not schedule:
        return None
    start = datetime.fromisoformat(schedule["start"].replace("Z", "+00:00"))
    interval = timedelta(hours=schedule.get("interval_hours", 24))
    when = start + index * interval
    return when.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("config", help="Path to batch_config.yaml")
    ap.add_argument("--dry-run", action="store_true", help="Print ffmpeg commands and skip upload for every video")
    args = ap.parse_args()

    config = yaml.safe_load(Path(args.config).read_text(encoding="utf-8"))
    defaults = config.get("defaults", {})
    videos = config.get("videos", [])
    schedule = defaults.get("schedule")

    if not videos:
        raise SystemExit("No videos listed under `videos:` in the config")

    results = []
    for i, entry in enumerate(videos):
        merged = {**defaults, **entry}
        merged.pop("schedule", None)

        publish_at = merged.pop("publish_at", None) or compute_publish_at(schedule, i)

        print(f"\n=== VIDEO {merged['video_number']} ({i + 1}/{len(videos)}) ===")
        try:
            result = run_single(
                content_file=merged["content_file"],
                video_number=merged["video_number"],
                clip=merged["clip"],
                audio=merged["audio"],
                hours=merged["hours"],
                output_dir=merged.get("output_dir", "output"),
                reencode=merged.get("reencode", False),
                video_bitrate=merged.get("video_bitrate", "2500k"),
                upload=merged.get("upload", False),
                privacy=merged.get("privacy", "private"),
                publish_at=publish_at,
                category_id=merged.get("category_id", "10"),
                thumbnail=merged.get("thumbnail"),
                dry_run=args.dry_run,
            )
            result["status"] = "ok"
            result["publish_at"] = publish_at
        except Exception as e:  # noqa: BLE001 - batch must continue past a bad entry
            result = {
                "video_number": merged["video_number"],
                "status": "FAILED",
                "error": str(e),
            }
            print(f"FAILED: {e}", file=sys.stderr)

        results.append(result)

    print("\n=== BATCH SUMMARY ===")
    ok = [r for r in results if r["status"] == "ok"]
    failed = [r for r in results if r["status"] == "FAILED"]
    for r in results:
        if r["status"] == "ok":
            yt = f" -> https://youtu.be/{r['youtube_id']}" if r.get("youtube_id") else ""
            when = f" (publishes {r['publish_at']})" if r.get("publish_at") else ""
            print(f"  [ok]     video {r['video_number']}: {r['output_path']}{yt}{when}")
        else:
            print(f"  [FAILED] video {r['video_number']}: {r['error']}")

    print(f"\n{len(ok)}/{len(results)} succeeded, {len(failed)} failed")
    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
