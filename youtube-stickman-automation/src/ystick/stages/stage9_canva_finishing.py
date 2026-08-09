from __future__ import annotations

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.canva_client import CanvaClient
from ystick.utils.files import read_json


class CanvaFinishingStage(Stage):
    name = "canva_finishing"

    def run(self, ctx: ProjectContext) -> dict:
        rough_cut = ctx.project_dir / STAGE_FOLDERS["video_assembly"] / "rough_cut.mp4"
        script = read_json(ctx.project_dir / STAGE_FOLDERS["script_generation"] / "script.json")

        client = CanvaClient(ctx.secrets, mock=ctx.mock)
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        out_path = out_dir / "branded_cut.mp4"

        fields = {"title": script["chosen_idea"]["title"], "channel_name": ctx.extra["blueprint"].name}
        client.apply_branding(rough_cut, out_path, fields, template_id=ctx.secrets.canva_brand_template_id)
        return {"output": str(out_path)}
