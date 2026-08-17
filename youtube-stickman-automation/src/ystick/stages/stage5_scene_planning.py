"""Deterministic scene segmentation from script + timestamps — no LLM call
needed (or cost) for this stage. Groups sentences into scenes within
[min_scene_seconds, max_scene_seconds], splits any single sentence that
alone exceeds the max, and flags very short trailing beats to hold the
previous scene's illustration instead of commissioning a new image."""
from __future__ import annotations

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.utils.files import read_json, write_json


def _split_oversized(sentence: dict, words: list[dict], max_ms: int) -> list[dict]:
    in_range = [w for w in words if sentence["start_ms"] <= w["start_ms"] < sentence["end_ms"]]
    if not in_range:
        return [sentence]
    pieces, current, piece_start = [], [], sentence["start_ms"]
    for w in in_range:
        current.append(w)
        if w["end_ms"] - piece_start >= max_ms:
            pieces.append({"text": " ".join(x["word"] for x in current), "start_ms": piece_start, "end_ms": w["end_ms"]})
            current, piece_start = [], w["end_ms"]
    if current:
        pieces.append({"text": " ".join(x["word"] for x in current), "start_ms": piece_start, "end_ms": sentence["end_ms"]})
    return pieces or [sentence]


def _build_scenes(sentences: list[dict], words: list[dict], min_ms: int, max_ms: int) -> list[dict]:
    expanded: list[dict] = []
    for sent in sentences:
        if sent["end_ms"] - sent["start_ms"] > max_ms:
            expanded.extend(_split_oversized(sent, words, max_ms))
        else:
            expanded.append(sent)

    scenes, buf, buf_start = [], [], None
    for sent in expanded:
        if buf_start is None:
            buf_start = sent["start_ms"]
        buf.append(sent)
        if sent["end_ms"] - buf_start >= min_ms:
            scenes.append(_finalize(buf, buf_start))
            buf, buf_start = [], None
    if buf:
        if scenes:
            last = scenes[-1]
            last["end_ms"] = buf[-1]["end_ms"]
            last["duration_ms"] = last["end_ms"] - last["start_ms"]
            last["narration_excerpt"] += " " + " ".join(s["text"] for s in buf)
        else:
            scenes.append(_finalize(buf, buf_start))
    return scenes


def _finalize(buf: list[dict], start_ms: int) -> dict:
    end_ms = buf[-1]["end_ms"]
    return {
        "start_ms": start_ms,
        "end_ms": end_ms,
        "duration_ms": end_ms - start_ms,
        "narration_excerpt": " ".join(s["text"] for s in buf),
    }


class ScenePlanningStage(Stage):
    name = "scene_planning"

    def run(self, ctx: ProjectContext) -> dict:
        transcript = read_json(ctx.project_dir / STAGE_FOLDERS["timestamps"] / "transcript.json")
        cfg = ctx.settings.stages.scene_planning
        min_ms = int(cfg.min_scene_seconds * 1000)
        max_ms = int(cfg.max_scene_seconds * 1000)

        scenes = _build_scenes(transcript["sentences"], transcript["words"], min_ms, max_ms)

        hold_threshold_ms = min_ms * 0.6
        for i, scene in enumerate(scenes):
            scene["scene_id"] = f"scene_{i + 1:03d}"
            scene["hold_previous_image"] = i > 0 and scene["duration_ms"] < hold_threshold_ms

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        write_json(out_dir / "storyboard.json", scenes)
        return {"num_scenes": len(scenes), "num_held": sum(s["hold_previous_image"] for s in scenes)}
