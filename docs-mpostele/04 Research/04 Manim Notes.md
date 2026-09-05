# Manim Notes

Manim is a strong fit for motion graphics in this project because it is deterministic, scriptable, and lightweight compared with AI-driven video synthesis.

## Use cases

- animated titles
- feature callouts
- arrow animation
- highlight boxes and UI emphasis
- product mockup overlays

## Advantages

- clean, code-driven animation
- highly controllable timing and transitions
- low memory compared with generative video models

## Implementation direction

Use Manim to generate transparent or solid-background motion layers that can be composited over screenshot footage or product stills.

## Current implementation

`pipeline/manim_scenes.py` defines two scenes, driven entirely by plain `Text` (no `MathTex`/LaTeX dependency):

- `TitleOverlayScene` -- a title card that fades in, holds, and fades out
- `CalloutOverlayScene` -- a highlight box with a label, positioned over a screen region

`pipeline/overlays.py` renders either scene as a transparent `.mov` clip via `manim render --transparent` and composites it over a base motion clip with FFmpeg's `overlay` filter (`build_manim_command`, `render_overlay`, `composite_overlay`). Run standalone with:

```bash
python -m pipeline.overlays --base-video artifacts/first_scene/motion.mp4 --overlay-type title --text "New feature"
```

Manim's rendering is CPU-only (Cairo), so it fits the project's no-GPU-required constraint; the pip package is listed in `requirements.txt`.

## Related notes

- [[03 Workflow/02 Animation Engine]]
- [[04 Research/01 Low-Memory Animation Options]]
