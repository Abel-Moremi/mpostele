# Video Rendering Path

This stage produces the short-form video from the `composition_spec` block written by `composition_agent` — the only video path in the pipeline now. It replaced two earlier approaches (local SD1.5 + AnimateDiff, remote Wan2.1 dispatch via Colab) that were removed once this path was confirmed reliably working; see [[04 Research/01 Local Diffusion Model Options]] for the full history of why.

## Composition Director Agent

`app/agents/composition_agent.py` (Ollama) produces a *data* spec — an ordered list of scenes, each naming one of three fixed components (`TitleReveal`, `CaptionOverlay`, `Outro`) plus duration and text/color props — never scene code. The scene generators themselves are hand-written once in `revideo/src/scenes/` and reused across every job.

## Composition Validator

`app/agents/composition_validator.py` is a deterministic gate (same shape as `quality_inspector.py`) that checks the spec's component names, prop completeness, and text/duration limits *before* a render is spawned — `revideo/src/schema.ts`'s Zod schema is the second half of that validation boundary, on the Node side. The orchestrator retries `composition_agent` up to `MAX_QUALITY_RETRIES` times on a failed check, then falls through and renders anyway rather than looping forever.

## Rendering engine

`app/media/video_engine.py` shells out to `node render.mjs` inside the sibling `revideo/` Node project (the repo's only non-Python toolchain — required, not optional; run `npm install` inside `revideo/` once, see the Setup Checklist). `revideo/render.mjs` calls `renderVideo()` from `@revideo/renderer` against `revideo/src/video-project.ts`, whose one master scene dispatches each `composition_spec` entry to the matching hand-written generator (`TitleReveal`/`CaptionOverlay`/`Outro`) — the same "data picks from a fixed table, never generates code" property `MainComposition.tsx` used to enforce. Output lands in `artifacts.raw_clip`, then feeds straight into `encode.py` — there's no interpolation stage, since Revideo renders natively at its target frame rate.

**Confirmed working end to end (2026-09-20)** against a live Ollama server, both the video and poster branches: `strategy -> script -> quality gate -> svg gate -> composition_agent -> composition_validator -> video_engine (revideo) -> encode -> platform_adaptor` produced a genuine `.mp4` (1080x1920, 30fps, `ffprobe`-confirmed), including a real SVG decoration rendered into the frame. Two real bugs surfaced while porting from Remotion, not code review, and were fixed:
1. Revideo's default exporter (`@revideo/core/wasm`) runs an in-browser WebAssembly FFmpeg build that never completes in a headless-Chromium subprocess (no cross-origin-isolation headers for the multithreaded build) — it just hangs. Fixed by forcing the server-side FFmpeg exporter (`@revideo/core/ffmpeg`) in both `revideo/src/video-project.ts` and `poster-project.ts`.
2. A `Txt` node's `text` prop bound to a reactive closure over a signal silently fails to render on every captured frame server-side (`"The scene is not available in the current context"`, swallowed internally — the node just renders blank, no thrown error). Fixed by driving text with imperative `tween()`/`.text(value, duration)` calls instead of a computed signal (see `revideo/src/scenes/caption-overlay.tsx`).

## Why Revideo, not Remotion

Remotion's license is source-available, not open source: free only for individuals, non-profits, and for-profit companies with 3 or fewer employees — past that a paid Company License is required. That sat in tension with this project's "keep the stack free and open source" goal. Revideo's packages are MIT-licensed. See [[07 Reference/02 Notes Archive]] for the full swap rationale.

## Privacy note

Nothing leaves the machine — Revideo renders entirely via a local headless-Chromium subprocess, and `render.mjs` disables Revideo's default telemetry ping.

## Frame interpolation and audio

No frame interpolation step exists any more (RIFE was removed along with the diffusion paths it served). FFmpeg multiplexes the narration/audio track and encodes the final H.264 output directly from Revideo's output.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
