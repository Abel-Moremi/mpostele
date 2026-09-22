# Video Rendering Path

This stage produces the short-form video from the `composition_spec` block written by `composition_agent` — the only video path in the pipeline now. It replaced two earlier approaches (local SD1.5 + AnimateDiff, remote Wan2.1 dispatch via Colab) that were removed once this path was confirmed reliably working; see [[04 Research/01 Local Diffusion Model Options]] for the full history of why.

## Narration Engine

`app/media/narration_engine.py` runs *before* composition: it synthesizes the Piper voiceover from `content.script_text` and probes its real duration with `ffprobe`, writing `narration.duration_seconds` to state. This runs ahead of `composition_agent` deliberately — see below.

## Composition Director Agent

`app/agents/composition_agent.py` (Ollama) produces a *data* spec — an ordered list of scenes, each naming one of three fixed components (`TitleReveal`, `CaptionOverlay`, `Outro`) plus text/color/transition props — never scene code. The scene generators themselves are hand-written once in `revideo/src/scenes/` and reused across every job.

Scene *duration* is not part of what the LLM decides. `narration_engine.py` splits `content.script_text` into one sentence-level segment per Piper synthesis call (merging any segment under `settings.MIN_CAPTION_SEGMENT_CHARS` into its neighbor), so `composition_agent.py` builds one `CaptionOverlay` scene per segment, each `durationInFrames` set in Python to exactly match that segment's real measured length; `TitleReveal`/`Outro` are fixed silent title-card beats (`settings.TITLE_REVEAL_SECONDS`/`OUTRO_HOLD_SECONDS`). The LLM's only remaining job is adapting the hook/call-to-action into `TitleReveal`/`Outro`'s on-screen text - it never sees or decides `CaptionOverlay`'s text or timing. Earlier, the LLM guessed all scene durations toward a fixed target with no knowledge of real narration length, which meant the render could either cut off narration mid-sentence or run dead silent before Outro - this ordering removes that failure mode, and per-sentence segments give the video real cut points instead of one continuous caption block.

`composition_agent.py` also assigns a `transitionOut` per cut (every scene except the last) from `{"crossfade", "slide", "matchCut"}`. The creative-tier model (`settings.OLLAMA_CREATIVE_MODEL`) proposes a choice per cut from the ordered sequence of every scene's on-screen text (`_propose_transitions`), picking whichever fits that cut's mood/pacing. Python remains the safety net - deterministic, seeded off `job_id` (same reproducible-but-varied approach `pick_music_track` in `audio_engine.py` already uses) - and overrides anything missing, invalid, or a repeat of the previous cut's transition, so the result is always valid by construction regardless of what the model proposed. That guarantee is why this doesn't need its own validator/retry gate. See the Transitions section below and `revideo/src/transitions.ts`.

## Transitions

Cuts between scenes are no longer hard swaps. Each scene module in `revideo/src/scenes/` splits into `mount()` (builds the node tree at rest, hidden) and `play()` (the entrance animation + hold, unchanged from before except it takes refs as a parameter). Every scene also mounts a small accent-colored "anchor" Rect at a fixed position outside its own flex layout - a different, layout-independent slot per scene type, so its position is known exactly at mount time.

`revideo/src/video-project.ts` mounts each scene, plays its entrance+hold (reserving a `TRANSITION_SECONDS`-long tail if there's a next scene, and a matching head reservation on the very first scene's own plain fade-in, so total elapsed time still equals the sum of every scene's `durationInFrames` exactly), then hands off to `revideo/src/transitions.ts`'s `runTransition`: `crossfade` (opacity), `slide` (both scenes' root+anchor translate together), or `matchCut` (the outgoing anchor's position/size/fill tweens to the incoming anchor's already-known rest values while the rest of the frame crossfades underneath - two nodes standing in for what reads as one shape traveling across the cut, falling back to `crossfade` if either side lacks an anchor).

`revideo/schema.mjs` is a plain-JS hand-maintained twin of `src/schema.ts` (render.mjs is a plain Node script, not processed by Vite/TS, so it can't import the `.ts` file directly) - **both must be updated together**. Missing this once already caused a real bug: `transitionOut` was added to `schema.ts` but not `schema.mjs`, so Zod's default key-stripping silently dropped it from every scene before it reached `video-project.ts`, and every cut rendered as a `crossfade` regardless of what `composition_agent.py` picked, with no error anywhere in the pipeline.

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

No frame interpolation step exists any more (RIFE was removed along with the diffusion paths it served). The narration voiceover is synthesized up front by `narration_engine.py` (see above), then `app/media/audio_engine.py` mixes it with a music bed after the video render (it needs the rendered clip's duration to probe, for the mix's fade timing) and `encode.py` multiplexes the result and encodes the final H.264 output directly from Revideo's output.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
