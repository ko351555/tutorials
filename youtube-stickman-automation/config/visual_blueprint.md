# Visual Blueprint — FILL THIS IN FOR YOUR CHANNEL

Fed into Stage 6 (Image Prompt Generation) on every single prompt, so the
character/palette/style stays locked across scenes. This is the file that
determines whether your stickman looks like "your" stickman in scene 40.

## Character Sheet
- Base character: TODO — e.g. "Simple stickman: circle head, single-line
  limbs, no facial features except two dot eyes and expressive eyebrow
  lines; no mouth unless speaking."
- Reference image: TODO — path or URL to the canonical character reference
  image; `image_gen_client.py` will pass this as a conditioning reference.
- Recurring secondary characters (if any): TODO

## Color Palette
- Background: TODO — e.g. "Off-white paper texture, #F7F3E9"
- Line color: TODO — e.g. "Warm black, #2B2B2B, consistent line weight"
- Accent colors (max N): TODO — list hex codes and what they're reserved for
  (e.g. one accent color per recurring "theme" object)

## Line & Rendering Style
- TODO: e.g. "Whiteboard-marker doodle style, slightly imperfect hand-drawn
  lines, no gradients, no shading except occasional single-color fill."

## Scene Continuity Rules
- TODO: e.g. "Camera/'canvas' stays static unless the script explicitly
  changes location — prefer adding/removing elements on the same canvas over
  cutting to a new background."
- When to hold the previous image instead of generating a new one: TODO
  (this feeds Stage 5's `hold_previous` decision — e.g. "hold whenever the
  next sentence elaborates on the same visual idea rather than introducing
  a new one").

## Negative Prompt / Things to Avoid
- TODO: e.g. "No text/lettering baked into the image, no realistic shading,
  no color outside the accent palette, no more than 2 characters on screen
  at once."

## Prompt Template (used verbatim by Stage 6, with `{scene_description}`
## filled in per scene)
```
{base_character_description}, {line_style}, {color_palette},
scene: {scene_description}, {continuity_notes}, {negative_prompt}
```
