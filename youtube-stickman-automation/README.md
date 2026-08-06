# YouTube Stickman/Doodle Automation Pipeline

Turns a video idea (or just a niche) into a finished, YouTube-ready
stickman/doodle explainer video by orchestrating ChatGPT Pro / Claude Code,
ElevenLabs, FoziScribe AI, Google Flow, and Canva into one pipeline with
retries, resume-on-failure, and configurable human-approval checkpoints.

Full design writeup: [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — start
there for the architecture, workflow diagram, tech stack rationale,
API-vs-browser-automation decisions, and the step-by-step rollout plan.

## Quickstart

```bash
cd youtube-stickman-automation
python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env        # fill in API keys (see .env.example for which stages need what)
# Fill in the three files that make this YOUR channel:
#   config/channel_blueprint.yaml  — identity: name, topics, cadence, contact, default video length
#   config/channel_style_guide.md  — how scripts should sound
#   config/visual_blueprint.md     — how images should look

# Dry run — exercises the full pipeline with fixture data, no API calls, no cost.
# Leave the idea blank to auto-pick from channel_blueprint.yaml's topics:
ystick new --mock
ystick run <project_id>
ystick status <project_id>   # shows the topic seed, target length, and mode it's running with

# A specific idea, custom length, once .env has real keys:
ystick new "why octopuses have three hearts" --minutes 10
ystick run <project_id>
```

Approval gates (topic selection, final review by default) pause the run and
print what to do next:

```bash
ystick approve <project_id> --stage topic_selection --select 2
```

## Interactive UI

For the full click-through experience — scored idea cards, an editable
script box, a live storyboard table, audio/image/video previews, and a
step-by-step progress tracker — run the Streamlit dashboard instead of the
CLI:

```bash
pip install -e '.[ui]'
ystick-ui
```

This opens a local browser tab (`localhost:8501`) with a project sidebar,
a 10-stage progress tracker, and a "Run pipeline" button that streams live
per-stage status. Every approval gate renders as a proper review screen —
pick a topic by clicking a card, edit the script inline, review the
storyboard as a table, watch the final cut before it's packaged — instead
of reading JSON in a terminal. See
[`docs/ARCHITECTURE.md` §11](docs/ARCHITECTURE.md#11-interactive-ui) for
how it's wired to the same orchestrator as the CLI.

## Project layout

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md#4-folder-structure) for the
full annotated tree. Short version: `src/ystick/stages/` has one file per
pipeline stage, `src/ystick/integrations/` has one client per external
service, `src/ystick/core/` has the orchestrator + state machine, and every
project's artifacts land under `data/projects/<project_id>/`.

## Tests

```bash
pytest tests/
```
