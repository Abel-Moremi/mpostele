# Poster Rendering Path

This stage produces a high-resolution static poster from the `keyframe_prompt` and `poster_layout` blocks written by the agent swarm.

## Background generation

- local SD1.5 or an SD1.5 LCM/Turbo derivative
- text-free background, generated strictly under ~2.5GB VRAM
- fp16 precision, negative-space regions reserved for text as constrained by the Keyframe Prompt Agent

## Vector canvas compositor

Pillow draws vector shapes, text overlays, badges, and logos on top of the generated background, using the `poster_layout.layers` array from `state.json` (position, font, max width, color, alignment).

## Text safety

Word wrapping is computed against `font.getbbox()` so lines stay inside `max_width_px`. This does not fully guarantee no overflow — a single token wider than the max width (a long URL or hashtag) will still overflow the box, since there's no automatic font-size shrink or truncation fallback yet. See [[04 Research/04 Pillow Compositor Notes]] for the known edge cases.

## Typical outputs

- `raw_background` — the SD1.5 text-free background
- `final_poster` — the composited output written to `artifacts.final_poster`

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/04 Pillow Compositor Notes]]
