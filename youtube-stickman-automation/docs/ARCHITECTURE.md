# YouTube Stickman/Doodle Video Automation — Architecture

Production-quality pipeline that turns a video idea (or just a niche) into a
finished, YouTube-ready stickman/doodle explainer video, orchestrating
ChatGPT Pro, Claude Code, ElevenLabs, FoziScribe AI, Google Flow and Canva
behind one system instead of ten manual tool switches.

Status: reference implementation. Text-generation stages (1, 2, 5, 6, 10) run
end-to-end today via Claude Code's headless mode. Media-service stages (3, 4,
7, 8, 9) are wired against real client interfaces with a `--mock` mode for
testing the orchestration without spending API credits — flip them to live
mode by dropping in credentials (see `config/settings.yaml` +
`.env`).

---

## 1. Overall Architecture

The system is a **durable pipeline of 10 stages**, each a pure function
`(ProjectContext) -> ProjectContext`, run by an **orchestrator** that owns
retries, state persistence, and approval gates. Every stage reads its inputs
from and writes its outputs to a **project directory** on disk
(`data/projects/<project_id>/`), so any stage can be re-run or resumed purely
from files + a small SQLite state table — no in-memory state survives a
crash.

```
                         ┌─────────────────────────────────────────────┐
                         │                Orchestrator                 │
                         │  (state machine · retries · approval gates) │
                         └───────────────┬───────────────────────────┘
                                          │ reads/writes
                                          ▼
                         ┌─────────────────────────────────────────────┐
                         │   SQLite state store  (runs.db)              │
                         │   project_id · stage · status · attempts    │
                         └─────────────────────────────────────────────┘
                                          │
     ┌────────────────────────────────────────────────────────────────┐
     │                     data/projects/<project_id>/                │
     │  01_ideas/ 02_script/ 03_audio/ 04_transcript/ 05_storyboard/   │
     │  06_prompts/ 07_images/ 08_assembly/ 09_final/ 10_packaging/    │
     └────────────────────────────────────────────────────────────────┘
                                          ▲
                                          │ each stage is isolated, idempotent,
                                          │ and only depends on prior stage's files
     ┌──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┬──────────┐
     │ Stage 1  │ Stage 2  │ Stage 3  │ Stage 4  │ Stage 5  │ Stage 6  │ Stage 7  │ Stage 8  │ Stage 9  │ Stage 10 │
     │ Topic    │ Script   │ Voice    │ Timestmp │ Scene    │ Image    │ Image    │ Video    │ Canva    │ YouTube  │
     │ Discovery│ Gen      │ Gen      │ Gen      │ Planning │ Prompts  │ Gen      │ Assembly │ Finish   │ Package  │
     └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
          │          │          │          │          │          │          │          │          │          │
      Claude     Claude    ElevenLabs  FoziScribe   Claude     Claude    Image-gen  FFmpeg +   Canva      Claude +
      Code       Code      API         (or Whisper  (reasoning (reasoning API (recon    Flow      Connect    YouTube
      headless   headless              fallback)    over       over       -sistency  (optional  API        Data API
                                                      script+    blueprint)  model)     motion     (Autofill+ v3
                                                      timestamps)                       enhance)   Export)
          ▲                                                                                                    │
          └──────────────────────── HUMAN APPROVAL GATES (optional, configurable) ─────────────────────────────┘
                 gate: topic          gate: script        gate: storyboard       gate: final cut/packaging
```

Design principles:

- **Stages are idempotent and file-addressed.** Re-running stage N with the
  same inputs produces the same outputs deterministically wherever the
  underlying API allows (image/audio generation is inherently
  non-deterministic — those stages are cached by content hash instead, so
  a re-run after a crash doesn't regenerate paid assets it already has).
- **The orchestrator, not the stages, owns cross-cutting concerns**: retry,
  backoff, logging, state transitions, approval gating. Stage code stays
  focused on "given these inputs, produce this output."
- **Every external integration lives behind an interface** in
  `src/ystick/integrations/`, so ElevenLabs, FoziScribe, Google Flow, and
  Canva are each swappable (e.g. FoziScribe → Whisper, Google Flow →
  pure-FFmpeg assembly) without touching stage or orchestrator code.
- **Claude Code itself is the default LLM backend**, not a separately
  billed OpenAI/Anthropic API key. Since the user already pays for Claude
  Code, all reasoning/text stages (1, 2, 5, 6, 10) shell out to
  `claude -p` in headless mode (see §6). ChatGPT can be wired in as an
  alternate provider for A/B'ing script style, but isn't required.

---

## 2. Workflow Diagram (stage detail + data flow)

```
 [ idea (optional) ]  -- blank falls back to config/channel_blueprint.yaml's topics
        │
        ▼
 ┌────────────────┐   writes ideas.json (5-8 scored ideas)
 │ 1. Topic        │──────────────────────────────────────┐
 │    Discovery    │                                       │
 └────────────────┘                                        ▼
        │                                     ●  APPROVAL GATE (pick 1, or auto-pick top score)
        ▼
 ┌────────────────┐   writes script.md + script.json (scene-tagged)
 │ 2. Script       │   uses config/channel_style_guide.md
 │    Generation   │
 └────────────────┘
        │                                     ●  APPROVAL GATE (optional — edit script.md in place)
        ▼
 ┌────────────────┐   writes narration.mp3 (ElevenLabs TTS, preferred voice_id)
 │ 3. Voice        │
 │    Generation   │
 └────────────────┘
        │
        ▼
 ┌────────────────┐   writes transcript.json (word + sentence timestamps)
 │ 4. Timestamp    │   FoziScribe AI primary, faster-whisper local fallback
 │    Generation   │
 └────────────────┘
        │
        ▼
 ┌────────────────┐   writes storyboard.json (scene list: start_ms, end_ms,
 │ 5. Scene        │   hold_previous: bool, est_duration_ms, narration_excerpt)
 │    Planning     │
 └────────────────┘
        │                                     ●  APPROVAL GATE (optional — review storyboard pacing)
        ▼
 ┌────────────────┐   writes image_prompts.json (1 prompt/scene, style-locked
 │ 6. Image Prompt │   via config/visual_blueprint.md + running character/palette
 │    Generation   │   continuity memory)
 └────────────────┘
        │
        ▼
 ┌────────────────┐   writes images/scene_001/*.png ... organized per scene,
 │ 7. Image        │   content-hash cached so re-runs don't re-spend credits
 │    Generation   │
 └────────────────┘
        │
        ▼
 ┌────────────────┐   writes assembly/rough_cut.mp4 (FFmpeg: pan/zoom,
 │ 8. Video        │   subtitle burn-in, narration mux, transitions);
 │    Assembly     │   optional Flow pass for hero-scene motion clips
 └────────────────┘
        │
        ▼
 ┌────────────────┐   writes final/branded_cut.mp4 via Canva Connect
 │ 9. Canva        │   Autofill + Export API against a pre-built brand
 │    Finishing    │   template (intro/outro/lower-thirds)
 └────────────────┘
        │                                     ●  APPROVAL GATE (final review before publish-ready packaging)
        ▼
 ┌────────────────┐   writes packaging.json (title/desc/tags/chapters/
 │ 10. YouTube     │   thumbnail concept/pinned comment/community post/
 │     Packaging   │   shorts variant) + optionally drafts upload via
 └────────────────┘   YouTube Data API (draft/private, human hits publish)
        │
        ▼
 [ finished video + packaging, ready for human "Publish" click ]
```

---

## 3. Technology Stack

| Layer | Choice | Why |
|---|---|---|
| Orchestration language | **Python 3.11+** | Best-supported SDKs for every target service (ElevenLabs, YouTube Data API, Canva Connect, FFmpeg wrappers), strong async/subprocess ergonomics for shelling out to Claude Code and FFmpeg. |
| LLM backend (default) | **Claude Code CLI, headless (`claude -p`)** | Already paid for; no separate API key/billing to manage for stages 1, 2, 5, 6, 10. |
| LLM backend (optional) | OpenAI API (ChatGPT) | Swappable provider for style A/B testing — requires its own API key, separate from ChatGPT Pro's chat subscription. |
| State store | **SQLite** (`runs.db`) | Zero-ops, file-based, transactional — perfect for a single-operator resume-on-failure system. Upgrade path to Postgres if this becomes multi-tenant/multi-worker (see §9). |
| Task queue (later) | **Redis + RQ** (optional, phase 2) | Only needed once you parallelize multiple videos concurrently; not required for v1's single-project-at-a-time flow. |
| Voice synthesis | **ElevenLabs REST API** | Official, documented, key-based — no browser automation needed. |
| Transcription | **FoziScribe AI (primary) / faster-whisper (local fallback)** | FoziScribe has no confirmed public API as of this writing — see §6 for the fallback strategy that keeps the pipeline unblocked either way. |
| Image generation | **API-based model with reference/style-locking** (e.g. OpenAI Images API `gpt-image-1` with reference images, or a dedicated consistency-oriented model) | Needs to support "give it a reference image + get a consistent character back" — the actual precondition for stickman continuity across scenes. Canva's Magic Media and Google Flow's built-in generator are UI-only today; keep them as manual/creative options, not the automated backbone. |
| Motion / hero-scene animation | **Google Flow (manual/optional)** + **FFmpeg (automated default)** | Flow has no public API (Google Labs product, browser-only) — treat it as an optional creative enhancement a human runs for 2-3 hero shots, not a pipeline dependency. FFmpeg (Ken Burns pan/zoom, crossfades, subtitle burn-in) is the dependable, scriptable backbone for 100% of scenes. |
| Branding/finishing | **Canva Connect API** (Autofill + Export) against a pre-built Brand Template | Real, documented, key-based API — as long as intro/outro/lower-thirds are pre-built once as a Canva template with named placeholders. |
| Publishing metadata/upload | **YouTube Data API v3** | Official; used to create the video as **unlisted/private draft** with full metadata, chapters, and thumbnail pre-set — a human clicks Publish. Community posts have no API — flagged as manual. |
| Secrets | **`.env` + `pydantic-settings`**, never committed | Standard 12-factor pattern; `.env.example` documents every required key. |
| Logging | **structlog** → JSON lines to `logs/<project_id>.log` + stdout | Structured logs are what let you grep "which stage failed on which project" across weeks of runs. |
| Retry | **tenacity** (exponential backoff + jitter, per-integration policies) | Battle-tested, declarative retry without hand-rolled backoff loops. |
| CLI | **Typer** | Thin, typed CLI (`ystick new`, `ystick run`, `ystick approve`, `ystick status`) with near-zero boilerplate. |
| Media processing | **ffmpeg-python** / raw `ffmpeg` subprocess | Deterministic, scriptable, free, no rate limits — the one piece of the pipeline you fully control. |
| Browser automation (fallback only) | **Playwright** | Reserved for the few surfaces with no API (FoziScribe if it stays API-less, Canva as a fallback, community posts) — isolated behind the same integration interfaces so it's opt-in and swappable. |
| Interactive UI | **Streamlit** | A local control-panel UI needs real widgets — audio players, image grids, a video player for final review — not a terminal. Streamlit gets all of that natively with almost no frontend code, sits directly on top of the same `Orchestrator`/`StateStore` the CLI uses (no separate API layer to maintain), and is the standard choice for exactly this kind of single-operator content-pipeline dashboard. See §11. |

---

## 4. Folder Structure

```
youtube-stickman-automation/
├── docs/
│   └── ARCHITECTURE.md              # this document
├── config/
│   ├── settings.yaml                # provider choices, model names, approval toggles
│   ├── scoring_weights.yaml         # Stage 1 idea-scoring rubric weights
│   ├── channel_blueprint.yaml       # channel identity: name, topics, cadence, contact, default length
│   ├── content_strategy.md          # what makes topics work: formula, CPM insight, starter ideas
│   ├── channel_style_guide.md       # narration voice/tone/structure rules (fill in yours)
│   └── visual_blueprint.md          # stickman style, palette, character sheet (fill in yours)
├── src/ystick/
│   ├── cli.py                       # Typer entrypoint: new / run / approve / status / resume
│   ├── config.py                    # pydantic-settings loader (.env + settings.yaml)
│   ├── logging_conf.py
│   ├── approvals.py                 # approval-gate logic + CLI prompts
│   ├── core/
│   │   ├── pipeline.py              # Stage base class, ProjectContext, retry decorator
│   │   ├── orchestrator.py          # state machine: run/resume/skip-completed
│   │   └── exceptions.py
│   ├── state/
│   │   ├── store.py                 # SQLite-backed run/stage state (resume capability)
│   │   └── models.py
│   ├── integrations/
│   │   ├── llm_client.py            # Claude Code headless / OpenAI / mock
│   │   ├── elevenlabs_client.py
│   │   ├── transcription_client.py  # FoziScribe / faster-whisper
│   │   ├── image_gen_client.py
│   │   ├── video_assembly.py        # FFmpeg pipeline (+ optional Flow hook)
│   │   ├── canva_client.py          # Canva Connect Autofill + Export
│   │   └── youtube_client.py        # YouTube Data API v3
│   ├── stages/
│   │   ├── stage1_topic_discovery.py
│   │   ├── stage2_script_generation.py
│   │   ├── stage3_voice_generation.py
│   │   ├── stage4_timestamps.py
│   │   ├── stage5_scene_planning.py
│   │   ├── stage6_image_prompts.py
│   │   ├── stage7_image_generation.py
│   │   ├── stage8_video_assembly.py
│   │   ├── stage9_canva_finishing.py
│   │   └── stage10_youtube_packaging.py
│   ├── ui/                          # Streamlit dashboard — see §11
│   │   ├── app.py                   # entrypoint: sidebar, stage tracker, run control
│   │   ├── gates.py                 # per-gate review screens + results view
│   │   ├── helpers.py               # cached orchestrator, safe media rendering
│   │   └── launcher.py              # `ystick-ui` console script
│   └── utils/
│       ├── retry.py
│       ├── ids.py
│       └── files.py
├── data/
│   └── projects/<project_id>/
│       ├── 01_ideas/ideas.json
│       ├── 02_script/script.md, script.json
│       ├── 03_audio/narration.mp3
│       ├── 04_transcript/transcript.json
│       ├── 05_storyboard/storyboard.json
│       ├── 06_prompts/image_prompts.json
│       ├── 07_images/scene_001/*.png ... scene_NNN/*.png
│       ├── 08_assembly/rough_cut.mp4
│       ├── 09_final/branded_cut.mp4
│       ├── 10_packaging/packaging.json
│       └── run_state.json           # human-readable mirror of the SQLite row
├── logs/<project_id>.log
├── tests/
├── pyproject.toml
└── .env.example
```

---

## 5. Automation Strategy

### 5.1 Job model
A "project" = one video, identified by a slug (`project_id`), e.g.
`why-octopuses-have-three-hearts-20260806`. Everything about that video lives
under `data/projects/<project_id>/`.

### 5.2 State machine
Each stage for a project has a row in SQLite:

```
runs(project_id, stage, status, attempts, last_error, payload_path, updated_at)
```

`status ∈ {pending, running, awaiting_approval, done, failed}`. The
orchestrator's `run(project_id)` loop:

1. Load (or create) the project's state row set.
2. Find the first stage that is not `done`.
3. If it's `awaiting_approval`, stop and report — nothing runs until a human
   (or an auto-approve policy) calls `ystick approve`.
4. Otherwise mark `running`, execute the stage with retry, and on success
   mark `done` (or `awaiting_approval` if the stage is gated) and continue
   to the next stage; on exhausted retries mark `failed` and stop.

### 5.3 Resume capability
Because state is on disk (SQLite row + stage output files), `ystick run
<project_id>` is always safe to re-invoke after a crash, an API outage, or a
laptop closing — it picks up exactly where it left off. Completed stages are
never silently re-executed (and never re-billed) unless you pass `--force
--from-stage N`.

### 5.4 Retry logic
`utils/retry.py` wraps each integration call with `tenacity`:
network/5xx/timeout errors retry with exponential backoff + jitter (default:
5 attempts, 2s→32s); validation errors (bad prompt, 4xx) do **not** retry —
they fail fast into `status=failed` with the error captured, since retrying
a malformed request just burns quota.

### 5.5 Approval checkpoints
Configurable in `config/settings.yaml` under `approvals:`. Default:

```yaml
approvals:
  topic_selection: true      # Stage 1 → 2
  script_review: false       # Stage 2 → 3 (edit script.md by hand if enabled)
  storyboard_review: false   # Stage 5 → 6
  final_review: true         # Stage 9 → 10, before packaging drafts the upload
```

When a gate is on, the orchestrator writes the stage's output, sets
`awaiting_approval`, and exits with a clear CLI message. The human reviews
the file (or, for topic selection, picks from the printed shortlist), then
runs `ystick approve <project_id> --stage <name> [--select N]`.

### 5.6 Progress tracking & logging
`ystick status <project_id>` prints the stage table with status/attempts/
timestamps. Every stage emits structured JSON log lines (stage, project_id,
duration_ms, tokens/credits used where applicable) to
`logs/<project_id>.log`, so a failed run three days ago is fully
reconstructable.

### 5.7 Secrets management
All credentials live in `.env` (git-ignored), loaded via
`pydantic-settings`. `.env.example` enumerates every key the system can use
and marks which are required vs optional per stage. Nothing is ever printed
to logs; the config loader redacts key-shaped values before logging its own
startup summary.

---

## 6. Integration Plan Per Service

### ChatGPT Pro / Claude Code — Stages 1, 2, 5, 6, 10 (text/reasoning)
**Default: Claude Code headless mode.** `llm_client.py` shells out to
`claude -p "<prompt>" --output-format json` (or uses the Agent SDK directly
if this orchestrator is itself invoked from within Claude Code, which is the
common case). This means stages 1/2/5/6/10 cost nothing beyond the existing
Claude Code subscription — no separate Anthropic or OpenAI API key required.
ChatGPT Pro is wired in as an **optional alternate provider** in the same
interface for style A/B testing, but needs its own OpenAI API key (the Pro
*chat* subscription does not include API credits).

### ElevenLabs — Stage 3 (voice)
Real, documented REST API (`POST /v1/text-to-speech/{voice_id}`). Store
`voice_id` in `config/settings.yaml`, API key in `.env`. Straightforward,
no browser automation needed. Long scripts are chunked at sentence
boundaries (ElevenLabs has a per-request character cap) and the resulting
clips concatenated with FFmpeg.

### FoziScribe AI — Stage 4 (timestamps/transcript)
No confirmed public API as of this writing. `transcription_client.py`
defines one interface, `transcribe(audio_path) -> Transcript`, with two
implementations behind it:
- `FoziScribeClient` — REST call stub, ready to fill in the moment API docs
  or an API key are available; falls back to browser automation
  (Playwright: upload file, poll for completion, download export) if
  FoziScribe stays UI-only.
- `WhisperLocalClient` — `faster-whisper` running locally, word-level
  timestamps, zero external dependency, works today with no account at all.
`settings.yaml` picks which implementation backs `transcription`, so this is
a one-line config change either direction with no stage code changes.

### Image generation — Stages 6-7
Needs consistent character/style across dozens of scenes — the actual hard
requirement. `image_gen_client.py` keeps a **running "style memory"** (the
character sheet from `visual_blueprint.md` + the previous scene's image as a
reference input) so scene N+1 stays visually continuous with scene N. Two
API providers are wired in:
- **`IMAGE_GEN_PROVIDER=openai`** (default) — OpenAI Images API. Needs its
  own billing, separate from a ChatGPT Pro chat subscription.
- **`IMAGE_GEN_PROVIDER=gemini`** — Google's Gemini API, genuinely
  free-tier to start (key from aistudio.google.com, no billing setup
  required). This is the same Imagen model family behind Google Flow —
  Flow itself is browser-only with no API, but the model powering it is
  reachable this way instead.

Google Flow and Canva's Magic Media stay UI-only, creative-only options —
neither exposes a scriptable API for image generation today.

**No image-gen API key? Set `IMAGE_GEN_PROVIDER=manual`.** This trades
automation for zero extra cost: an `image_upload` approval gate fires after
Stage 6 showing every scene's prompt (copy into ChatGPT — already covered
by a Pro subscription — or any image tool) with an upload slot right next
to it in the UI. Stage 7 then just verifies the files exist and builds the
manifest from them instead of calling an API — everything downstream
(assembly, branding, packaging) is unaffected. CLI users without the UI can
drop files straight into `07_images/<scene_id>/image.png` and run
`ystick approve <id> --stage image_upload`.

### Google Flow — Stage 8 (optional motion enhancement)
No public API (Google Labs, browser-only, invite/subscription gated). Not on
the automated critical path. `video_assembly.py`'s default path is 100%
FFmpeg: Ken Burns pan/zoom on each still, crossfade transitions, subtitle
burn-in from the Stage 4 transcript, narration mux. Flow is documented as an
optional manual step: a human can take 2-4 "hero" scene images into Flow,
generate a short motion clip, and drop the resulting file into
`08_assembly/hero_clips/` — `video_assembly.py` detects and splices in any
file present there before the automated pass, so the manual step augments
rather than blocks the pipeline.

### Canva — Stage 9 (branding/finishing)
Canva Connect APIs are real and documented: **Autofill API** populates a
pre-built Brand Template's named fields (intro text, outro card, lower
thirds, logo placeholder) and the **Export API** renders the result. This
requires a one-time manual step: build the branded template once in Canva's
editor with named placeholder fields, then reference its `template_id` in
`config/settings.yaml`. `canva_client.py` implements the API path as
default and a Playwright fallback (open the template, autofill via UI,
trigger export, download) behind the same interface for anything the
Autofill API can't reach (e.g. certain animation presets).

### YouTube — Stage 10 (packaging + optional upload)
YouTube Data API v3 (official, key/OAuth-based) creates the video as a
**private/unlisted draft** with title, description, tags, chapters (as
description timestamps), and thumbnail already set — nothing goes public
without a human clicking Publish. Community posts have no public API and
are flagged in `packaging.json` as a manual step with the drafted copy ready
to paste in.

---

## 7. APIs vs. Browser Automation

| Service | Path | Status |
|---|---|---|
| Claude Code | Headless CLI (`claude -p`) | ✅ API-equivalent, default |
| ChatGPT (optional) | OpenAI REST API | ✅ Real API, needs separate key |
| ElevenLabs | REST API | ✅ Real API |
| FoziScribe AI | Unknown — REST stub + Playwright fallback | ⚠️ Unverified; local Whisper fallback recommended as the reliable default |
| Image generation | REST API (reference-image capable model) | ✅ Real API |
| Google Flow | Browser only (Google Labs) | ❌ No API — manual/optional enhancement only |
| Canva | Connect API (Autofill + Export) | ✅ Real API, requires one-time template setup; Playwright fallback for edge cases |
| YouTube upload/metadata | YouTube Data API v3 | ✅ Real API |
| YouTube Community posts | None | ❌ No API — manual, copy is pre-drafted |

**Rule of thumb applied throughout:** prefer a documented API behind a
retryable, logged client; reserve Playwright browser automation for the
handful of surfaces that genuinely have no API, isolate it behind the same
integration interface as its API sibling, and treat it as higher-maintenance
(UI changes silently break it — these paths get extra logging and a "manual
fallback" runbook note).

---

## 8. Human Approval Checkpoints

| Gate | Default | Why here |
|---|---|---|
| After Stage 1 (topic) | **On** | Highest-leverage 10-second decision in the whole pipeline — everything downstream is wasted spend if the wrong idea is picked. |
| After Stage 2 (script) | Off (opt-in) | Turn on while you're still dialing in the style guide; turn off once the style guide reliably produces on-voice scripts. |
| After Stage 5 (storyboard) | Off (opt-in) | Useful early on to sanity-check pacing/scene count before spending image-gen credits on 40 prompts. |
| After Stage 6 (`image_upload`) | **Auto — on whenever `IMAGE_GEN_PROVIDER=manual`** | Not a settings.yaml toggle like the others; it's derived from that provider choice, since it's only relevant when there's no image-gen API key to call automatically. |
| After Stage 9 (final cut) | **On** | Last check before packaging drafts a real YouTube upload — catch any visual/audio glitch before it's "ready to publish." |
| Community post / thumbnail upload | **Always manual** | No API exists; pipeline hands you drafted copy and files, you paste/upload. |
| Publish button | **Always manual** | The system never auto-publishes; Stage 10 leaves the video as a private/unlisted draft by design. |

All gates except `image_upload` are toggles in `config/settings.yaml` —
dial them down as you trust the pipeline more, or up while testing a new
niche/style.

---

## 9. Scalability Recommendations

- **v1 (this scaffold): single project at a time, single machine.** SQLite +
  local filesystem is intentionally the whole stack — no infra to run.
- **Batch mode (near-term):** the orchestrator's project loop already
  supports being called for N project_ids in sequence (`ystick run
  --all-pending`); safe today, just slower than parallel.
- **Parallel workers (phase 2):** swap SQLite for Postgres and put stage
  execution behind Redis + RQ (or Celery). Each stage becomes a queued job;
  multiple workers pull from the queue, so 5 videos can be in Stage 3-8
  simultaneously. The state-store interface (`state/store.py`) is already
  written against an abstract repository so this swap doesn't touch stage or
  orchestrator code.
- **Cost control at scale:** image and voice generation dominate per-video
  cost. Content-hash caching (already in Stage 7) means re-runs are free;
  add a per-project budget cap in `settings.yaml` that halts before Stage 7
  if projected image-gen spend exceeds a threshold.
- **Multi-channel:** `config/channel_style_guide.md` and
  `visual_blueprint.md` are per-channel by design — point `settings.yaml` at
  a different config directory per channel and the same codebase runs N
  channels with zero code changes.
- **Observability at scale:** structured JSON logs are already the format;
  the next step when running unattended is shipping them to a place you can
  alert on (even a simple daily digest of `failed` rows from `runs.db` is
  enough at this scale — no need for a full observability stack until
  you're running double-digit videos/day).

---

## 10. Step-by-Step Implementation Plan

1. **Fill in the three blueprint files** — `config/channel_blueprint.yaml`
   (channel identity: name, topics, upload cadence, contact, default video
   length), `config/channel_style_guide.md` (narration voice, pacing, CTA
   conventions), and `config/visual_blueprint.md` (character sheet,
   palette, line weight, background style). These are the actual creative
   IP; the pipeline is worthless without them being specific. The channel
   blueprint is what Stage 1 falls back to when a project is created with
   no explicit idea, and what the UI shows as branding.
2. **Set `.env`** from `.env.example`: ElevenLabs API key + voice_id, image-gen
   API key, Canva Connect credentials + brand template_id, YouTube OAuth
   client. Claude Code needs no key (see §6).
3. **Run in mock mode first**: `ystick new "test idea" --mock` exercises the
   full state machine and folder structure end-to-end with fixture data, at
   zero cost — verifies the orchestration before any paid API is touched.
4. **Turn on Stage 1-2 live** (Claude Code only, free): validate topic
   scoring and script quality against the style guide; iterate on the style
   guide until scripts need no manual editing.
5. **Turn on Stage 3-4 live** (ElevenLabs + transcription): confirm voice
   quality and timestamp accuracy on a real script.
6. **Turn on Stage 5-7 live** (storyboard + image prompts + image gen): this
   is where character-consistency tuning happens — expect several passes on
   `visual_blueprint.md` to lock in continuity.
7. **Build the Canva brand template once** (intro/outro/lower-thirds with
   named placeholder fields), record its `template_id`, turn on Stage 9.
8. **Turn on Stage 8 (FFmpeg assembly) and Stage 10 (packaging + draft
   upload)**, run one full video end-to-end, watch the private/unlisted
   draft land in YouTube Studio.
9. **Tune approval gates** down as trust builds; add the budget cap once
   you're comfortable running unattended.
10. **(Optional) Move to batch/parallel** once producing more than ~1
    video/day, per §9.

---

## 11. Interactive UI

Running everything through the CLI is fine for automation, but reviewing a
storyboard or a generated character image as raw JSON in a terminal is not
a real workflow. `src/ystick/ui/` is a Streamlit dashboard built directly
on the same `Orchestrator`/`StateStore` the CLI uses — no separate API
layer, no state duplication, no drift between the two.

```bash
pip install -e '.[ui]'
ystick-ui           # opens http://localhost:8501
```

What it gives you that the CLI can't:

- **Live stage tracker** — all 10 stages as a row of status icons
  (pending/running/awaiting-approval/done/failed), updated in real time as
  `Orchestrator.iter_run()` streams one event per stage.
- **Real approval screens, not JSON dumps** — topic selection renders as
  scored, clickable idea cards; script review is an editable text box that
  writes straight back to `script.md`/`script.json`; storyboard review is a
  proper table of scene timing/pacing; final review plays the actual
  branded cut with `st.video`.
- **Asset browser** — script text, a narration audio player, the generated
  image grid, and the storyboard table, all in one expandable panel so you
  can sanity-check any stage's output without touching the filesystem.
- **One-click retry** — a failed stage shows its error inline with a Retry
  button that re-invokes the same resumable `iter_run()` the CLI uses, so
  behavior is identical either way.
- **Advanced panel** — a `force-from` reset exposed as a dropdown, for
  power users who want to re-run from a specific stage without deleting
  existing output.

Architecturally, `iter_run()` (in `core/orchestrator.py`) is what makes
this possible: it's a generator that yields one `StageEvent` per stage
(`running` → `done`/`failed`/`awaiting_approval`) instead of blocking until
the whole run finishes. The CLI's `run()` is now just `iter_run()` drained
to its last event — the UI and CLI share one code path end to end, so a
bug fix or new stage never needs to be wired up twice.

The dashboard is a single-operator local tool by design (matches the
system's overall v1 scope in §9) — it talks to the same on-disk
`data/projects/` and `runs.db` the CLI does, so you can freely switch
between clicking through the UI and resuming the same project from the
CLI (`ystick run <project_id>`) mid-pipeline. This was verified end-to-end
with a scripted browser test driving the real app through every stage and
every approval gate to completion.
