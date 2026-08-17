# Channel Style Guide — The Stickman Blueprint

This file is fed verbatim into Stage 2 (Script Generation) as the style
contract the LLM must follow. Channel identity (name, topics, cadence,
contact) lives in `config/channel_blueprint.yaml` — this file is purely
about *how scripts should sound*. Sharpen the TODOs below with real
examples as you produce videos; the more specific this gets, the less
manual editing every script needs.

## Voice & Tone
Derived from the channel tagline "Complex ideas. Simple visuals.
Actionable frameworks." — every script should:
- Take one complex psychology/money/productivity/AI concept and reduce it
  to its simplest correct form. No jargon without an immediate
  plain-English translation.
- End on something actionable — a framework, a rule of thumb, a concrete
  next step — not just an interesting fact.
- TODO: pin down the narrator's actual voice more precisely — e.g. tone
  (calm authority vs. energetic), first/second person, how much humor.

## Narration Structure
- Hook (0:00-0:10): open with the surprising or counterintuitive claim the
  video resolves — never "Hi guys, welcome back."
- Setup (0:10-0:45): frame the problem/question in terms the viewer
  recognizes from their own life (money, habits, career, mindset).
- Body: walk through the idea via the "complex idea → simple visual"
  pattern — one concept per beat, concrete before abstract.
- Payoff: land the actionable framework explicitly — name it, make it
  repeatable/memorable.
- Outro + CTA: TODO — subscribe ask wording, mention of the 2-week upload
  cadence, end-screen behavior.

## Pacing Rules
- New idea/beat at least every 15-20 seconds of narration — this drives
  Stage 5 scene segmentation directly.
- Target runtime is set per-project (default from
  `channel_blueprint.yaml` → `target_video_length_minutes`, overridable at
  creation time in the UI or via `ystick new --minutes N`).

## Content Pillars (from channel_blueprint.yaml)
Every script should clearly sit under one of: money, mindset, career
growth, habits, AI, self improvement. If an idea doesn't map cleanly to one
of these, it's probably off-channel.

## Vocabulary & Phrases
- Preferred: TODO — plain, concrete language; name frameworks so they're
  quotable ("the two-list rule", etc.)
- Avoid: TODO (clichés, hustle-culture filler, vague self-help platitudes)

## Sample Script Excerpt (few-shot anchor)
Paste 1-2 paragraphs of a script you consider "perfectly on-voice" here —
this is the single highest-leverage thing in this file for matching your
exact tone.

```
TODO: paste sample narration here
```
