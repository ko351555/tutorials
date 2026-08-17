"""Shorts is a second, cheap output derived from assets the long-form
pipeline already paid for — no new image generation, no re-scripting from
scratch. An LLM call picks the strongest standalone 40-50s window from the
existing narration/storyboard (defaulting to the video's opening hook if it
can't decide), then that window's audio, scenes, and subtitles are trimmed
and reassembled vertically (9:16) with the same `build_video()` used for
the long-form cut.
"""
from __future__ import annotations

from pathlib import Path

from ystick.core.exceptions import FatalError
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.canva_client import CanvaClient
from ystick.integrations.video_assembly import build_video, trim_audio, write_srt
from ystick.utils.files import parse_json_loose, read_json, write_json

SYSTEM_PROMPT = """You pick the single strongest standalone excerpt from a
video's narration to repurpose as a YouTube Short. Respond with ONLY a
JSON object, no prose."""

PROMPT_TEMPLATE = """Full narration script:
---
{script_text}
---

Sentence-level timestamps (ms):
{sentence_list}

Total narration length: {total_ms}ms.

Pick the {min_s}-{max_s} second contiguous window (by sentence boundaries)
that works best as a standalone YouTube Short — it must make sense with NO
context from the rest of the video AND land on a genuine conclusion: a
complete hook and payoff, ending on an actual punchline/reveal/takeaway
sentence — never a fragment that trails off mid-buildup, references "as I
said before," or stops right before the payoff would land. This channel's
videos are structured hook -> framework -> steps -> punchy takeaway, so the
video's OPENING alone is rarely a complete arc on its own — it's usually
just the setup. Prefer either (a) the hook plus its immediate payoff/reveal
if that lands within the window, or (b) the closing reframe/takeaway
moment, which is more reliably self-contained since it's already the
resolution. Do not pick a window whose last sentence is still building up
to something the window doesn't include.

Respond with a JSON object: {{"start_ms": <int, a sentence's start_ms>,
"end_ms": <int, a sentence's end_ms>, "reason": "<one line>"}}.
"""


def _fallback_window(sentences: list[dict], min_s: int, max_s: int) -> tuple[int, int]:
    """Used when the LLM's pick is missing/invalid/off-brief. Anchors to the
    video's actual ending rather than its opening: per this channel's
    hook -> framework -> steps -> takeaway structure, the closing sentences
    are the resolution and reliably self-contained, whereas "the first N
    seconds" is almost always mid-setup with no payoff yet — exactly the
    "cuts off mid-story" failure mode this replaces. Always snapped to
    sentence boundaries so it never cuts mid-sentence either."""
    if not sentences:
        return 0, 0
    end_ms = sentences[-1]["end_ms"]
    max_ms = max_s * 1000
    start_ms = sentences[0]["start_ms"]
    for sent in reversed(sentences):
        if end_ms - sent["start_ms"] > max_ms:
            break
        start_ms = sent["start_ms"]
    return start_ms, end_ms


def _select_window(ctx: ProjectContext, script_text: str, sentences: list[dict], min_s: int, max_s: int) -> tuple[int, int]:
    total_ms = sentences[-1]["end_ms"] if sentences else 0
    fallback = _fallback_window(sentences, min_s, max_s)

    sentence_list = "\n".join(f"[{s['start_ms']}-{s['end_ms']}] {s['text']}" for s in sentences)
    prompt = PROMPT_TEMPLATE.format(
        script_text=script_text,
        sentence_list=sentence_list,
        total_ms=total_ms,
        min_s=min_s,
        max_s=max_s,
    )
    raw = ctx.extra["llm"].complete(prompt, system=SYSTEM_PROMPT, json_mode=True, mock_key="shorts_excerpt")
    try:
        picked = parse_json_loose(raw)
        start_ms, end_ms = int(picked["start_ms"]), int(picked["end_ms"])
    except (KeyError, TypeError, ValueError, FatalError):
        # parse_json_loose itself raises FatalError when the response has
        # no JSON in it at all — window selection is an enhancement over
        # a sane default (the video's opening), never worth failing the
        # whole stage over.
        return fallback

    if not (0 <= start_ms < end_ms <= total_ms):
        return fallback
    # Give the LLM some slack (it's picking sentence boundaries, not hitting
    # an exact duration) but don't accept something wildly off-brief — a
    # full-video-length "excerpt" isn't a Short.
    duration_s = (end_ms - start_ms) / 1000
    if duration_s > max_s * 1.5 or duration_s < min_s * 0.4:
        return fallback
    return start_ms, end_ms


def _slice_scenes(storyboard: list[dict], manifest: dict, start_ms: int, end_ms: int) -> list[dict]:
    scenes = []
    for scene in storyboard:
        overlap_start = max(scene["start_ms"], start_ms)
        overlap_end = min(scene["end_ms"], end_ms)
        if overlap_end <= overlap_start:
            continue
        entry = manifest.get(scene["scene_id"])
        if not entry:
            continue
        scenes.append({
            "scene_id": scene["scene_id"],
            "image_path": Path(entry["path"]),
            "duration_ms": overlap_end - overlap_start,
        })
    if not scenes and storyboard:
        # Nothing overlapped (shouldn't happen once start/end are validated
        # against real sentence boundaries) — fall back to the first scene
        # with an image rather than handing build_video an empty list.
        first = next((s for s in storyboard if s["scene_id"] in manifest), None)
        if first:
            scenes = [{
                "scene_id": first["scene_id"],
                "image_path": Path(manifest[first["scene_id"]]["path"]),
                "duration_ms": min(first["duration_ms"], end_ms - start_ms) or 1000,
            }]
    return scenes


def _slice_sentences(sentences: list[dict], start_ms: int, end_ms: int) -> list[dict]:
    sliced = []
    for sent in sentences:
        overlap_start = max(sent["start_ms"], start_ms)
        overlap_end = min(sent["end_ms"], end_ms)
        if overlap_end <= overlap_start:
            continue
        sliced.append({
            "text": sent["text"],
            "start_ms": overlap_start - start_ms,
            "end_ms": overlap_end - start_ms,
        })
    return sliced


class ShortsCreationStage(Stage):
    name = "shorts_creation"

    def run(self, ctx: ProjectContext) -> dict:
        script = read_json(ctx.project_dir / STAGE_FOLDERS["script_generation"] / "script.json")
        storyboard = read_json(ctx.project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")
        transcript = read_json(ctx.project_dir / STAGE_FOLDERS["timestamps"] / "transcript.json")
        manifest = read_json(ctx.project_dir / STAGE_FOLDERS["image_generation"] / "manifest.json")
        narration_path = ctx.project_dir / STAGE_FOLDERS["voice_generation"] / "narration.mp3"

        cfg = ctx.settings.stages.shorts_creation
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]

        # Per-project override wins when set (from the new-project checkbox);
        # None means "fall back to the settings.yaml global default," which
        # is what every project created before the checkbox existed carries.
        project_choice = ctx.extra.get("generate_short")
        should_run = cfg.enabled if project_choice is None else bool(project_choice)
        if not should_run:
            return {"skipped": True, "reason": "generate_short=False for this project"}

        start_ms, end_ms = _select_window(
            ctx, script["text"], transcript["sentences"], cfg.target_seconds_min, cfg.target_seconds_max
        )

        trimmed_narration = trim_audio(narration_path, start_ms, end_ms, out_dir / "narration_short.mp3", mock=ctx.mock)
        srt_path = write_srt(_slice_sentences(transcript["sentences"], start_ms, end_ms), out_dir / "narration_short.srt")
        scenes = _slice_scenes(storyboard, manifest, start_ms, end_ms)

        raw_path = out_dir / "shorts_raw.mp4"
        build_video(
            scenes,
            trimmed_narration,
            srt_path,
            raw_path,
            fps=cfg.fps,
            resolution="1080x1920",
            ken_burns=cfg.ken_burns,
            subtitles=True,
            mock=ctx.mock,
        )

        # Separate vertical (9:16) Brand Template from the long-form one —
        # Canva templates render at whatever canvas size they were built
        # with, so the 16:9 template can't be reused here. Gracefully
        # skips to an unbranded pass-through if not configured, same as
        # Stage 9 for the long-form video.
        out_path = out_dir / "shorts_cut.mp4"
        fields = {"title": script["chosen_idea"]["title"], "channel_name": ctx.extra["blueprint"].name}
        client = CanvaClient(ctx.secrets, mock=ctx.mock)
        client.apply_branding(raw_path, out_path, fields, template_id=ctx.secrets.canva_shorts_brand_template_id)

        return {
            "start_ms": start_ms,
            "end_ms": end_ms,
            "duration_s": round((end_ms - start_ms) / 1000, 1),
            "num_scenes": len(scenes),
            "output": str(out_path),
        }
