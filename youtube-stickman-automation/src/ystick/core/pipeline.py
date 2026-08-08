"""Stage base class + ProjectContext — the contract every pipeline stage
implements. Stages read/write files under ctx.project_dir; they don't talk
to the state store directly (the orchestrator owns that)."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ystick.config import AttrDict, Secrets


@dataclass
class ProjectContext:
    project_id: str
    project_dir: Path
    settings: AttrDict
    secrets: Secrets
    mock: bool = False
    seed_idea: str = ""
    log: Any = None
    extra: dict[str, Any] = field(default_factory=dict)

    def stage_dir(self, name: str) -> Path:
        d = self.project_dir / name
        d.mkdir(parents=True, exist_ok=True)
        return d


class Stage(ABC):
    name: str

    @abstractmethod
    def run(self, ctx: ProjectContext) -> dict:
        """Execute the stage. Must be idempotent given the same on-disk
        inputs. Returns a small JSON-serializable summary for logging."""
        raise NotImplementedError


# Canonical stage order. The orchestrator, CLI, and state store all key off
# this list — it's the single source of truth for pipeline sequencing.
STAGE_ORDER: list[str] = [
    "topic_discovery",
    "script_generation",
    "voice_generation",
    "timestamps",
    "scene_planning",
    "image_prompts",
    "image_generation",
    "video_assembly",
    "canva_finishing",
    "youtube_packaging",
]

# Folder each stage owns under data/projects/<id>/
STAGE_FOLDERS: dict[str, str] = {
    "topic_discovery": "01_ideas",
    "script_generation": "02_script",
    "voice_generation": "03_audio",
    "timestamps": "04_transcript",
    "scene_planning": "05_storyboard",
    "image_prompts": "06_prompts",
    "image_generation": "07_images",
    "video_assembly": "08_assembly",
    "canva_finishing": "09_final",
    "youtube_packaging": "10_packaging",
}

# Short human-readable labels — shared by the CLI and UI so stage naming
# never drifts between the two.
STAGE_LABELS: dict[str, str] = {
    "topic_discovery": "Topic",
    "script_generation": "Script",
    "voice_generation": "Voice",
    "timestamps": "Timestamps",
    "scene_planning": "Storyboard",
    "image_prompts": "Prompts",
    "image_generation": "Images",
    "video_assembly": "Assembly",
    "canva_finishing": "Branding",
    "youtube_packaging": "Packaging",
}

# One-line "what happens here" for each stage — shown as a reference legend
# in the UI so it's clear what to expect before you get there, not just
# once you're already at that stage's gate.
STAGE_DESCRIPTIONS: dict[str, str] = {
    "topic_discovery": "Generates and scores video ideas from your seed (or the channel's topics if left blank).",
    "script_generation": "Writes the full narration script for the idea you picked, in your channel's voice.",
    "voice_generation": "Sends the script to ElevenLabs and gets back narration audio.",
    "timestamps": "Transcribes the narration to get word- and sentence-level timestamps.",
    "scene_planning": "Splits the narration into scenes based on pacing, deciding where images change.",
    "image_prompts": "Writes one image-generation prompt per scene, keeping style/character consistent.",
    "image_generation": "Turns each prompt into an image — via API, or your manual upload if configured.",
    "video_assembly": "Assembles the images, narration, subtitles, and pan/zoom into a rough-cut video.",
    "canva_finishing": "Applies branding (intro/outro) via Canva to produce the finished cut.",
    "youtube_packaging": "Drafts title, description, tags, chapters, thumbnail concept, and social copy.",
}
