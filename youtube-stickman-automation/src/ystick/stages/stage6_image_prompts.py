from __future__ import annotations

from ystick.config import PROJECT_ROOT
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.utils.files import read_json, write_json

SYSTEM_PROMPT = """You write single-paragraph image generation prompts for a
stickman/doodle YouTube channel. Follow the visual blueprint exactly.
Respond with ONLY the prompt text, no prose, no quotes."""

PROMPT_TEMPLATE = """Visual blueprint:
---
{blueprint}
---

Previous scene's image prompt (for visual continuity, may be empty for the
first scene): {previous_prompt}

This is scene {scene_index} of {scene_total}.

This scene's narration — the EXACT words the viewer hears while this image
is on screen: "{narration}"

Before writing the prompt, privately identify: what is the ONE specific,
concrete visual metaphor or symbol that represents THIS EXACT sentence —
not the video's topic in general, not a generic illustration of "a person
thinking." If the narration says "not time, a feeling," that's a crossed-
out calendar next to a heart, not a stickman looking at a clock. If it
names a bias/rule, that's the name rendered on screen, not an abstract
mood shot. If it's a contrast (before/after, then/now, them/you), stage
both sides in one frame. Reuse the SAME specific symbol/metaphor across
consecutive scenes when the narration is still elaborating the same point
— introduce a new one only when the narration actually moves to a new
idea.

Stage the scene with motion, gesture, and interaction (pointing, reacting,
confronting, comparing) rather than a static figure standing there — per
the blueprint, decide whether this exact line is one of the video's few
most quotable/reframing moments and, if so, follows the On-Image Text
Captions rule (short, exact-words-from-this-line caption); most scenes
should have no caption at all.

Write one image generation prompt for this scene, per the blueprint's
prompt template, keeping character/palette/continuity consistent with the
previous scene unless the narration clearly introduces something new.
"""


class ImagePromptsStage(Stage):
    name = "image_prompts"

    def run(self, ctx: ProjectContext) -> dict:
        storyboard = read_json(ctx.project_dir / STAGE_FOLDERS["scene_planning"] / "storyboard.json")
        blueprint_path = PROJECT_ROOT / ctx.settings.channel.visual_blueprint_path
        blueprint = blueprint_path.read_text()

        prompts = []
        previous_prompt = ""
        previous_scene_id = None
        scene_total = len(storyboard)
        for scene_index, scene in enumerate(storyboard, start=1):
            if scene["hold_previous_image"]:
                prompts.append({"scene_id": scene["scene_id"], "reuse_scene": previous_scene_id})
                continue

            prompt_text = ctx.extra["llm"].complete(
                PROMPT_TEMPLATE.format(
                    blueprint=blueprint,
                    previous_prompt=previous_prompt or "(none — this is the first scene)",
                    scene_index=scene_index,
                    scene_total=scene_total,
                    narration=scene["narration_excerpt"],
                ),
                system=SYSTEM_PROMPT,
                mock_key="scene_prompt",
            ).strip()

            prompts.append({"scene_id": scene["scene_id"], "prompt": prompt_text})
            previous_prompt = prompt_text
            previous_scene_id = scene["scene_id"]

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        write_json(out_dir / "image_prompts.json", prompts)
        num_generated = sum(1 for p in prompts if "prompt" in p)
        return {"num_prompts": num_generated, "num_reused": len(prompts) - num_generated}
