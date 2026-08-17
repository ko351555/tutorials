import json
from pathlib import Path

from ystick.config import Secrets, load_blueprint, load_settings
from ystick.core.pipeline import ProjectContext
from ystick.stages.stage1_topic_discovery import TopicDiscoveryStage


class _RecordingLLMClient:
    def __init__(self, ideas):
        self.ideas = ideas
        self.calls = []

    def complete(self, prompt, *, system=None, json_mode=False, mock_key="generic"):
        self.calls.append({"prompt": prompt, "system": system})
        return json.dumps(self.ideas)


def _make_ctx(project_dir: Path, llm, seed_idea: str = "") -> ProjectContext:
    settings = load_settings()
    blueprint = load_blueprint(settings)
    return ProjectContext(
        project_id="content-strategy-test",
        project_dir=project_dir,
        settings=settings,
        secrets=Secrets(),
        mock=False,
        seed_idea=seed_idea,
        extra={"llm": llm, "blueprint": blueprint},
    )


def test_content_strategy_reaches_the_system_prompt(tmp_path: Path):
    ideas = [{"title": "Test Idea", "one_line_pitch": "pitch", "viral_potential": 8}]
    llm = _RecordingLLMClient(ideas)
    ctx = _make_ctx(tmp_path, llm)

    TopicDiscoveryStage().run(ctx)

    assert len(llm.calls) == 1
    system_prompt = llm.calls[0]["system"]
    # Key phrases from config/content_strategy.md should be present verbatim
    # in the system prompt — i.e. the file is actually being read and
    # injected, not just referenced in settings.yaml.
    assert "Counterintuitive hook" in system_prompt
    assert "money/psychology crossover" in system_prompt.lower() or "money/psychology crossover" in system_prompt


def test_blank_seed_falls_back_to_channel_topics(tmp_path: Path):
    ideas = [{"title": "Test Idea", "one_line_pitch": "pitch", "viral_potential": 8}]
    llm = _RecordingLLMClient(ideas)
    ctx = _make_ctx(tmp_path, llm, seed_idea="")

    TopicDiscoveryStage().run(ctx)

    prompt = llm.calls[0]["prompt"]
    assert "none given" in prompt
    assert "money" in prompt  # one of the channel's configured topics
