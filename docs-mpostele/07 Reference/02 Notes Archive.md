# Notes Archive

This is the archive for lower-priority or exploratory notes that are not yet part of the active workflow.

Use it for:

- experiments
- prototype ideas
- iterative notes that may later become formal decisions
- old ideas retained for future reference

## Superseded architecture (retired)

The project's original design used Playwright screenshot capture, Manim overlays, and FFmpeg Ken Burns motion instead of diffusion models, on the reasoning that AnimateDiff/SVD-class models needed too much VRAM for this hardware. That design was retired in favor of a diffusion-based architecture (LLM agent swarm + SD1.5 poster/video generation + remote Wan2.1 dispatch), which kept diffusion models in scope by making every stage transient and explicitly memory-unloaded rather than excluding them outright.

That diffusion-based architecture was itself later retired, once a third option — Remotion (code-driven rendering, no diffusion model at all) — was confirmed reliably working for both the video and poster paths. See [[04 Research/01 Local Diffusion Model Options]] for the measured reasons it won out. Full detail on both prior approaches is preserved in git history rather than duplicated here.

## Remotion → Revideo (2026-09-20)

Remotion itself was later swapped for Revideo, same code-driven rendering approach, different renderer: Remotion's license requires a paid Company License for any for-profit org above 3 employees, in tension with this project's "keep the stack free and open source" goal; Revideo's packages are MIT-licensed. A spike project first confirmed Revideo could produce comparable output and surfaced two real, non-obvious render-pipeline bugs (documented in [[03 Workflow/03 Video Rendering Path]]) before the actual scene port began. The four scene components (`TitleReveal`, `CaptionOverlay`, `Outro`, `Poster`) were ported 1:1 from React/`useCurrentFrame`/`interpolate`/`spring` to Revideo's generator/`tween` model, with one deliberate behavior change: `CaptionOverlay`'s word-by-word `<span>` fade-in (no equivalent in Revideo's flex layout engine, which doesn't do CSS-style paragraph reflow of independently-animated inline nodes) became a single wrapped `Txt` node with a progressive `.text(value, duration)` reveal instead - visually a very close substitute, not pixel-identical motion. Remotion's `still` single-frame render mode also has no Revideo equivalent (`renderVideo()`/`renderPartialVideo()` explicitly reject the image-sequence exporter); the poster path instead renders a near-zero-duration clip through the normal video path and extracts frame 0 with `ffmpeg -frames:v 1`.

## Related notes

- [[07 Reference/01 Links]]
