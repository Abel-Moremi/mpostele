# Poster Rendering Path

This stage produces a high-resolution static poster from the `poster_layout` block written by `poster_layout_agent` — Revideo-rendered, replacing the earlier SD1.5-background + Pillow-compositor approach (see [[04 Research/01 Local Diffusion Model Options]] and [[04 Research/04 Pillow Compositor Notes]] for why that path was dropped).

## Poster Composition Agent

`app/agents/poster_layout_agent.py` (Ollama) produces a small data spec: `headline`, `ctaText` (a short 2-4 word label, never the full call-to-action sentence), and two colors (`backgroundColor`, `accentColor`). This is a genuine simplification over the old Pillow-based version — Revideo handles text wrapping and positioning itself, so the prompt no longer needs canvas dimensions, x/y coordinates, or a `max_width_px` budget.

## Poster Validator

`app/agents/poster_validator.py` is a deterministic gate (same shape as `quality_inspector.py`/`composition_validator.py`): required keys present, `headline`/`ctaText` length caps. Runs before a render is spawned; the orchestrator retries `poster_layout_agent` up to `MAX_QUALITY_RETRIES` times on failure, then falls through and renders anyway.

## Rendering engine

`app/media/poster_engine.py` shells out to `node render.mjs --project poster` against `revideo/src/scenes/poster.tsx`, a static generator (no tweens, since only frame 0 is ever captured) combining a headline and a CTA badge, styled consistently with the video path's `TitleReveal`/`Outro` scenes. Revideo has no single-frame "still" render mode the way Remotion did — `render.mjs` works around this by rendering a near-zero-duration clip through the normal FFmpeg-exporter path, then extracting frame 0 with `ffmpeg -frames:v 1` and discarding the intermediate video. The output PNG is copied directly to `artifacts.final_poster` — no separate background-generation + compositing step.

## Fonts

`app/media/assets/fonts/` is no longer used — Revideo/CSS renders all text itself, so there's no `.ttf` file to source or license separately the way the old Pillow compositor needed. Brand fonts (Crimson Pro, Inter) are self-hosted via `@fontsource` packages in `revideo/`, not fetched from a CDN at render time.

## Typical outputs

- `final_poster` — the rendered PNG, written to `artifacts.final_poster`

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/04 Pillow Compositor Notes]]
