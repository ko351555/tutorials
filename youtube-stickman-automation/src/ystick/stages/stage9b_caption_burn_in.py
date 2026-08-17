from __future__ import annotations

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.video_assembly import burn_captions


class CaptionBurnInStage(Stage):
    """Runs after Branding so captions land on the actual final cut
    (intro/outro included, once Canva branding is wired up for real)
    instead of only the pre-branding rough cut."""

    name = "caption_burn_in"

    def run(self, ctx: ProjectContext) -> dict:
        branded_cut = ctx.project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"
        srt_path = ctx.project_dir / STAGE_FOLDERS["video_assembly"] / "narration.srt"

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        out_path = out_dir / "final_cut.mp4"

        burn_captions(branded_cut, srt_path, out_path, mock=ctx.mock)
        return {"output": str(out_path)}
