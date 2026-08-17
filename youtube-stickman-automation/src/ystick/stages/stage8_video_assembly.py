from __future__ import annotations

from pathlib import Path

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.video_assembly import build_video, write_srt
from ystick.utils.files import read_json


class VideoAssemblyStage(Stage):
    name = "video_assembly"

    def run(self, ctx: ProjectContext) -> dict:
        storyboard = read_json(ctx.project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")
        manifest = read_json(ctx.project_dir / STAGE_FOLDERS["image_generation"] / "manifest.json")
        transcript = read_json(ctx.project_dir / STAGE_FOLDERS["timestamps"] / "transcript.json")
        narration_path = ctx.project_dir / STAGE_FOLDERS["voice_generation"] / "narration.mp3"

        cfg = ctx.settings.stages.video_assembly
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]

        scenes = [
            {
                "scene_id": s["scene_id"],
                "image_path": Path(manifest[s["scene_id"]]["path"]),
                "duration_ms": s["duration_ms"],
            }
            for s in storyboard
        ]

        srt_path = write_srt(transcript["sentences"], out_dir / "narration.srt")
        hero_clips_dir = ctx.project_dir / cfg.hero_clips_dir

        out_path = out_dir / "rough_cut.mp4"
        build_video(
            scenes,
            narration_path,
            srt_path,
            out_path,
            fps=cfg.fps,
            resolution=cfg.resolution,
            ken_burns=cfg.ken_burns,
            subtitles=cfg.subtitles,
            hero_clips_dir=hero_clips_dir,
            mock=ctx.mock,
        )
        return {"num_scenes": len(scenes), "output": str(out_path)}
