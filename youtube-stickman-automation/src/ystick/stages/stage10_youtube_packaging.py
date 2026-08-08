from __future__ import annotations

from ystick.config import PROJECT_ROOT
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

Visual blueprint (for thumbnail_prompts — match this channel's art style
exactly, same as the in-video images):
---
{visual_blueprint}
---

Generate a JSON object with keys:
- title: viral, <=100 chars
- description: SEO-optimized, includes a natural CTA and a one-line
  business-inquiries mention at the end
- tags: array of 15-20 strings — REQUIRED, never empty; a mix of broad
  (channel topic) and specific (video subject) search terms
- thumbnail_text: <=5 words, the on-thumbnail caption
- thumbnail_prompts: array of exactly 5 complete, ready-to-paste
  image-generation prompts (for ChatGPT/DALL-E/Gemini), each a distinct
  thumbnail concept for this video, each following the visual blueprint's
  style/character/palette so it matches the video
- chapters: array of {{"time","label"}}
- pinned_comment, community_post, shorts_title, shorts_description
"""


class YoutubePackagingStage(Stage):
    name = "youtube_packaging"

    def run(self, ctx: ProjectContext) -> dict:
        script = read_json(ctx.project_dir / STAGE_FOLDERS["script_generation"] / "script.json")
        storyboard = read_json(ctx.project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")
        blueprint = ctx.extra["blueprint"]
        visual_blueprint = (PROJECT_ROOT / ctx.settings.channel.visual_blueprint_path).read_text()

        prompt = PROMPT_TEMPLATE.format(
            channel_name=blueprint.name,
            tagline=blueprint.tagline,
            business_email=blueprint.business_email,
            youtube_url=blueprint.youtube_url,
            title=script["chosen_idea"]["title"],
            script_excerpt=script["text"][:1000],
            num_scenes=len(storyboard),
            visual_blueprint=visual_blueprint,
        )
        raw = ctx.extra["llm"].complete(prompt, system=SYSTEM_PROMPT, json_mode=True, mock_key="packaging")
        packaging = parse_json_loose(raw)

        # LLM compliance safety net: tags/thumbnail_prompts are the two
        # fields most likely to get dropped by a model that otherwise
        # follows the JSON schema — never leave the packaging output with
        # nothing there to copy into YouTube Studio.
        if not packaging.get("tags"):
            packaging["tags"] = list({
                *[t.lower() for t in blueprint.topics],
                blueprint.name.lower(),
                *script["chosen_idea"]["title"].lower().split(),
            })
        if not packaging.get("thumbnail_prompts"):
            fallback_concept = packaging.get("thumbnail_concept") or script["chosen_idea"]["title"]
            packaging["thumbnail_prompts"] = [
                f"{fallback_concept} — variation {i + 1}. {visual_blueprint[:300]}" for i in range(5)
            ]

        cfg = ctx.settings.stages.youtube_packaging
        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]

        upload_result = {"status": "skipped"}
        if cfg.upload_as:
            final_cut = ctx.project_dir / STAGE_FOLDERS["caption_burn_in"] / "final_cut.mp4"
            client = YouTubeClient(ctx.secrets, mock=ctx.mock)
            upload_result = client.create_draft(
                final_cut,
                {"title": packaging["title"], "description": packaging["description"], "tags": packaging["tags"]},
                privacy=cfg.upload_as,
            )
        packaging["youtube_upload"] = upload_result

        write_json(out_dir / "packaging.json", packaging)
        return {"title": packaging["title"], "upload_status": upload_result["status"]}
