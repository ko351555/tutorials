from __future__ import annotations

import yaml

from ystick.config import PROJECT_ROOT
from ystick.core.pipeline import STAGE_FOLDERS, ProjectContext, Stage
from ystick.utils.files import parse_json_loose, write_json

SYSTEM_PROMPT_TEMPLATE = """You generate viral YouTube video ideas for "{name}" — {tagline}
{description}
Every idea must fit the channel's core topics: {topics}.

Content strategy for this channel — follow it closely:
{content_strategy}

Respond with ONLY a JSON array, no prose."""

PROMPT_TEMPLATE = """Seed (a specific idea the creator wants, or blank to pick
freely from the channel's core topics): {seed}

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
        blueprint = ctx.extra["blueprint"]
        content_strategy_path = PROJECT_ROOT / ctx.settings.channel.content_strategy_path
        content_strategy = content_strategy_path.read_text() if content_strategy_path.exists() else "(none provided)"

        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            name=blueprint.name,
            tagline=blueprint.tagline,
            description=blueprint.description.strip(),
            topics=", ".join(blueprint.topics),
            content_strategy=content_strategy,
        )
        # No idea given -> topic discovery isn't handed a vague generic
        # fallback, it's told to pick from this channel's actual topics.
        seed = ctx.seed_idea.strip() or f"(none given — pick from: {', '.join(blueprint.topics)})"

        prompt = PROMPT_TEMPLATE.format(
            seed=seed,
            num_ideas=cfg.num_ideas,
            criteria=", ".join(weights.keys()),
            criteria_keys=", ".join(weights.keys()),
        )
        raw = ctx.extra["llm"].complete(prompt, system=system_prompt, json_mode=True, mock_key="topic_ideas")
        ideas = parse_json_loose(raw)

        for idea in ideas:
            idea["weighted_score"] = round(
                sum(idea.get(k, 0) * w["weight"] for k, w in weights.items()), 2
            )
        ideas.sort(key=lambda i: i["weighted_score"], reverse=True)

        out_dir = ctx.project_dir / STAGE_FOLDERS[self.name]
        write_json(out_dir / "ideas.json", ideas)
        return {"num_ideas": len(ideas), "top_score": ideas[0]["weighted_score"] if ideas else None}
