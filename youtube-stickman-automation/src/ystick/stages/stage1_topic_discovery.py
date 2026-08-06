from __future__ import annotations

import yaml

from ystick.config import PROJECT_ROOT
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.utils.files import parse_json_loose, write_json

SYSTEM_PROMPT = """You generate viral YouTube video ideas for a stickman/doodle
educational animation channel. Respond with ONLY a JSON array, no prose."""

PROMPT_TEMPLATE = """Seed (a specific idea, or just a niche/topic area): {seed}

Generate {num_ideas} distinct, high-potential video ideas for this channel.
For each idea, score 1-10 on each of: {criteria}.

Respond as a JSON array of objects with keys: title, one_line_pitch,
{criteria_keys}.
"""


class TopicDiscoveryStage(Stage):
    name = "topic_discovery"

    def run(self, ctx: ProjectContext) -> dict:
        cfg = ctx.settings.stages.topic_discovery
        weights_path = PROJECT_ROOT / cfg.scoring_weights_path
        weights = yaml.safe_load(weights_path.read_text())["criteria"]

        prompt = PROMPT_TEMPLATE.format(
            seed=ctx.seed_idea or "general audience science/history/psychology facts",
            num_ideas=cfg.num_ideas,
            criteria=", ".join(weights.keys()),
            criteria_keys=", ".join(weights.keys()),
        )
        raw = ctx.extra["llm"].complete(prompt, system=SYSTEM_PROMPT, json_mode=True, mock_key="topic_ideas")
        ideas = parse_json_loose(raw)

        for idea in ideas:
            idea["weighted_score"] = round(
                sum(idea.get(k, 0) * w["weight"] for k, w in weights.items()), 2
            )
        ideas.sort(key=lambda i: i["weighted_score"], reverse=True)

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        write_json(out_dir / "ideas.json", ideas)
        return {"num_ideas": len(ideas), "top_score": ideas[0]["weighted_score"] if ideas else None}
