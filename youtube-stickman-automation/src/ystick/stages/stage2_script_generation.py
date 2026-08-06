from __future__ import annotations

from ystick.config import PROJECT_ROOT
from ystick.core.exceptions import FatalError
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.utils.files import read_json, write_json

SYSTEM_PROMPT_TEMPLATE = """You are a scriptwriter for "{name}" — {tagline}
Follow the channel style guide exactly. Output plain narration text only —
no scene directions, no markdown headers."""

PROMPT_TEMPLATE = """Channel style guide:
---
{style_guide}
---

Write a complete narration script for this video idea:
Title: {title}
Pitch: {pitch}

Target length: ~{minutes} minutes of spoken narration.
"""


class ScriptGenerationStage(Stage):
    name = "script_generation"

    def run(self, ctx: ProjectContext) -> dict:
        ideas_dir = ctx.project_dir / STAGE_FOLDERS["topic_discovery"]
        ideas = read_json(ideas_dir / "ideas.json")

        selection = (ctx.extra.get("approvals") or {}).get("topic_selection")
        idx = selection.get("select", 0) if selection else 0
        if idx >= len(ideas):
            raise FatalError(f"selected idea index {idx} out of range (have {len(ideas)} ideas)")
        chosen = ideas[idx]

        style_guide_path = PROJECT_ROOT / ctx.settings.channel.style_guide_path
        style_guide = style_guide_path.read_text()
        blueprint = ctx.extra["blueprint"]

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(name=blueprint.name, tagline=blueprint.tagline)
        prompt = PROMPT_TEMPLATE.format(
            style_guide=style_guide,
            title=chosen["title"],
            pitch=chosen["one_line_pitch"],
            minutes=ctx.extra["target_minutes"],
        )
        script_text = ctx.extra["llm"].complete(prompt, system=system_prompt, mock_key="script")

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "script.md").write_text(script_text)
        write_json(out_dir / "script.json", {"chosen_idea": chosen, "text": script_text})
        return {"chosen_title": chosen["title"], "script_chars": len(script_text)}
