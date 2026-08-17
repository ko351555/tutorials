# Visual Blueprint — The Stickman Blueprint

Fed into Stage 6 (Image Prompt Generation) on every single prompt, so the
character/palette/style stays locked across scenes. This is the file that
determines whether your stickman looks like "your" stickman in scene 40.

## Character Sheet
- Base character: Simple stickman — perfect circle head, thin single-line
  limbs, no facial features except two small dot eyes and one or two
  expressive eyebrow lines (no mouth unless the moment calls for shock/
  speech — then a simple open-oval mouth). Body: a plain colored
  short-sleeve shirt (color varies by character, see palette), no other
  clothing detail. Hands are simple 3-4 line "mitten" shapes, no fingers
  drawn individually except when pointing.
- Reference image: `config/reference_character.png` if present — passed as
  a conditioning reference by `image_gen_client.py` on every call after the
  first, so leave this section as the source of truth for the written
  description even if a reference image exists.
- Recurring secondary characters: none fixed — a second stickman appears
  whenever the narration needs a dialogue/conflict/contrast partner (e.g.
  "the person who gets it" vs. "the person who doesn't"), styled
  identically to the base character but with a different shirt color from
  the palette below, so multiple people on screen stay visually distinct
  without breaking the single-character-style rule.

## Color Palette
- Background: warm neutral, either off-white/paper (#F7F3E9) for
  process/explainer scenes, or a warm tan/sand (#E8C99B–#D9B571 range) for
  emotional/reflective or "big idea" scenes — pick whichever better matches
  the scene's tone, but stay consistent within a single scene.
- Line color: warm black (#1A1A1A), consistent bold line weight throughout
  — this is a doodle, not a fine sketch.
- Accent colors (max 4, each reserved for a purpose so viewers learn to
  read them):
  - Blue (#2E6FE0) — the "protagonist"/narrator stickman's shirt
  - Green (#3FA34D) — a second character, or "growth/positive" objects
  - Orange/red (#E0592E) — emphasis, warning, "the problem," arrows/circles
    drawing attention to a specific detail
  - Yellow (#F2C230) — ideas, insight, the "aha" moment (lightbulbs, sparks)
- Props (tables, calendars, phones, charts, etc.) render in a muted brown/
  wood tone (#A9793F) or flat gray — never full color, so accent colors stay
  reserved for meaning, not decoration.

## Line & Rendering Style
- Whiteboard-marker doodle style: bold, slightly imperfect hand-drawn
  lines, flat single-color fills only — no gradients, no shading, no
  photorealistic rendering, no cross-hatching. Everything reads clearly at
  thumbnail size.

## On-Image Text Captions — ENABLED
This channel's format leans on short, bold on-image text to land the
video's key reframes and contrasts — not decoration, a core storytelling
tool. Add a caption when a scene represents:
- the video's central reframe or counterintuitive claim (e.g. "NOT TIME, A
  FEELING"), typically as a standalone or near-standalone graphic scene
- a named framework/bias/rule being introduced (render its name directly,
  e.g. "THE 1% RULE," "BIRD IN HAND BIAS")
- a stark before/after or two-sided contrast (e.g. "THE PAST" / "THE
  PRESENT" as labels on each side)
- a big number/stat that's the point of the scene
Do NOT caption every scene — most scenes should be pure visual metaphor
with no text at all; captions are reserved for the 2-4 moments per video
that most deserve to be quotable and screenshot-able. When used:
- 2-6 words max, drawn from or directly adapted from that scene's actual
  narration line — never generic filler
- bold, heavy sans-serif, all-caps, black, centered or top-of-frame,
  large enough to read at thumbnail size
- the caption is the headline of the scene — compose the rest of the
  drawing to support it (e.g. a crossed-out calendar icon next to "NOT
  TIME, A FEELING," not a busy unrelated background)

## Scene Continuity Rules
- Canvas/"camera" stays static (same background, same framing) unless the
  narration explicitly shifts to a new idea, location, or time period —
  prefer adding/removing elements on the same canvas over cutting to a new
  background, so the video feels like one continuous drawing being built up
  rather than a slideshow.
- Hold the previous image instead of generating a new one whenever the
  next sentence elaborates on, restates, or gives an example of the same
  visual idea rather than introducing a new one — this also feeds Stage 5's
  `hold_previous` pacing decision.

## Negative Prompt / Things to Avoid
No photorealism, no realistic shading or gradients, no color outside the
defined accent palette, no more than 2 characters on screen at once, no
cluttered/busy backgrounds, no small illegible details, no stock-photo
style, no watermarks or logos, no text unless it follows the On-Image Text
Captions rule above (and when used, only the intended short caption — no
extra labels, no filler words, no lorem-ipsum-style placeholder text).

## Prompt Template (used verbatim by Stage 6, with `{scene_description}`
## filled in per scene)
```
{base_character_description}, {line_style}, {color_palette},
scene: {scene_description}, {on_image_text_if_any}, {continuity_notes},
{negative_prompt}
```
