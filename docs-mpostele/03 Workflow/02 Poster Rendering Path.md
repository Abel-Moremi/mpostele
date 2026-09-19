# Poster Rendering Path

This stage produces a high-resolution static poster from the `keyframe_prompt` and `poster_layout` blocks written by the agent swarm.

## Background generation

- local SD1.5 or an SD1.5 LCM/Turbo derivative
- **confirmed working end to end on the target 1050 Ti (2026-09-18/19) at 512x896** (`settings.POSTER_GEN_WIDTH/HEIGHT`), ~2min for 20 steps. The original guess of 768x1344 was never actually validated and OOM'd on the real card (4.13GB already allocated, needed 1.94GB more) even with attention slicing on — SD1.5 was trained at 512x512, and going well beyond that scales attention memory sharply. 512x896 is the confirmed-working floor; raising it is untested.
- fp16 precision, negative-space regions reserved for text as constrained by the Keyframe Prompt Agent

## Vector canvas compositor

Pillow draws vector shapes, text overlays, badges, and logos on top of the generated background, using the `poster_layout.layers` array from `state.json` (position, font, max width, color, alignment).

**Two real bugs found and fixed by an actual end-to-end run, not code review:**
- The Poster Composition Agent's prompt originally showed a hardcoded `1080x1920` example canvas while the real render was 512x896 — it placed text at `x=540` (clipped off the right edge of a 512px-wide image) and a badge at `y=1600` (entirely below the bottom of an 896px-tall image, invisible). Fixed by feeding the agent the *real* canvas size from `settings.py` instead of an arbitrary example (`app/agents/poster_layout_agent.py`).
- The button-badge renderer had no text wrapping or width clamping at all — it drew the badge's full text at its natural width regardless of the canvas, so a long call-to-action sentence ran off both edges. Fixed to wrap badge text and size the rounded-rectangle background to fit (`app/media/compositor.py`).
- Notably, telling the agent explicitly ("button_badge text must be 2-4 words, never the full call-to-action") plus a short worked example did **not** reliably stop it from using the full sentence anyway — unlike the earlier script/keyframe prompt fixes, a concrete example alone wasn't enough here. The compositor-level wrap/clamp is the real fix; the prompt constraint is best-effort on top of it, not load-bearing.

## Text safety

Word wrapping is computed against `font.getbbox()` so lines stay inside `max_width_px`, for both text layers and button badges. This does not fully guarantee no overflow — a single token wider than the max width (a long URL or hashtag) will still overflow the box, since there's no automatic font-size shrink or truncation fallback yet. See [[04 Research/04 Pillow Compositor Notes]] for the known edge cases.

## Fonts

`app/media/assets/fonts/` is empty by default and gitignored — no font is bundled or licensed for distribution. Local testing borrowed a system font (Arial, temporarily renamed `Inter-Bold.ttf`) and removed it afterward; a real deployment needs a properly licensed `.ttf` placed there before the compositor can run.

## Typical outputs

- `raw_background` — the SD1.5 text-free background
- `final_poster` — the composited output written to `artifacts.final_poster`

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/04 Pillow Compositor Notes]]
