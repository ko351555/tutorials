from __future__ import annotations

from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.integrations.youtube_client import YouTubeClient
from ystick.utils.files import parse_json_loose, read_json, write_json

SYSTEM_PROMPT = """You are a YouTube growth strategist. Respond with ONLY a
JSON object, no prose."""

PROMPT_TEMPLATE = """Channel: {channel_name} — {tagline}
Business inquiries: {business_email}
Channel URL: {youtube_url}

Video title/topic: {title}
Script excerpt (first 1000 chars): {script_excerpt}
Number of scenes: {num_scenes}

Generate a JSON object with keys:
title (viral, <=100 chars), description (SEO-optimized, includes a natural
CTA and a one-line business-inquiries mention at the end), tags (array of
15-20 strings), thumbnail_text (<=5 words), thumbnail_concept (one sentence
describing the visual), chapters (array of {{"time","label"}}),
pinned_comment, community_post, shorts_title, shorts_description.
"""


class YoutubePackagingStage(Stage):
    name = "youtube_packaging"

    def run(self, ctx: ProjectContext) -> dict:
        script = read_json(ctx.project_dir / STAGE_FOLDERS["script_generation"] / "script.json")
        storyboard = read_json(ctx.project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")
        blueprint = ctx.extra["blueprint"]

        prompt = PROMPT_TEMPLATE.format(
            channel_name=blueprint.name,
            tagline=blueprint.tagline,
            business_email=blueprint.business_email,
            youtube_url=blueprint.youtube_url,
            title=script["chosen_idea"]["title"],
            script_excerpt=script["text"][:1000],
            num_scenes=len(storyboard),
        )
        raw = ctx.extra["llm"].complete(prompt, system=SYSTEM_PROMPT, json_mode=True, mock_key="packaging")
        packaging = parse_json_loose(raw)

        cfg = ctx.settings.stages.youtube_packaging
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]

        upload_result = {"status": "skipped"}
        if cfg.upload_as:
            branded_cut = ctx.project_dir / STAGE_FOLDERS["canva_finishing"] / "branded_cut.mp4"
            client = YouTubeClient(ctx.secrets, mock=ctx.mock)
            upload_result = client.create_draft(
                branded_cut,
                {"title": packaging["title"], "description": packaging["description"], "tags": packaging["tags"]},
                privacy=cfg.upload_as,
            )
        packaging["youtube_upload"] = upload_result

        write_json(out_dir / "packaging.json", packaging)
        return {"title": packaging["title"], "upload_status": upload_result["status"]}
