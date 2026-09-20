# Video Rendering Path

This stage produces the short-form video from the `composition_spec` block written by `composition_agent` — the only video path in the pipeline now. It replaced two earlier approaches (local SD1.5 + AnimateDiff, remote Wan2.1 dispatch via Colab) that were removed once this path was confirmed reliably working; see [[04 Research/01 Local Diffusion Model Options]] for the full history of why.

## Composition Director Agent

`app/agents/composition_agent.py` (Ollama) produces a *data* spec — an ordered list of scenes, each naming one of three fixed components (`TitleReveal`, `CaptionOverlay`, `Outro`) plus duration and text/color props — never JSX. The scene components themselves are hand-written once in `remotion/src/scenes/` and reused across every job, following Remotion's stated best practices: `useCurrentFrame`/`interpolate`/`spring` only (never CSS `@keyframes`, which desyncs under headless frame-by-frame capture), `<Series>`/`<Sequence>` for scene timing.

## Composition Validator

`app/agents/composition_validator.py` is a deterministic gate (same shape as `quality_inspector.py`) that checks the spec's component names, prop completeness, and text/duration limits *before* a render is spawned — `remotion/src/schema.ts`'s Zod schema is the second half of that validation boundary, on the Node side. The orchestrator retries `composition_agent` up to `MAX_QUALITY_RETRIES` times on a failed check, then falls through and renders anyway rather than looping forever.

## Rendering engine

`app/media/video_engine.py` shells out to `npx remotion render` inside the sibling `remotion/` Node project (the repo's only non-Python toolchain — required, not optional; run `npm install` inside `remotion/` once, see the Setup Checklist). Output lands in `artifacts.raw_clip`, then feeds straight into `encode.py` — there's no interpolation stage, since Remotion renders natively at its target frame rate (no low-frame-count generative source to upsample the way AnimateDiff/Wan2.1 output needed).

**Confirmed working end to end (2026-09-19)** against a live Ollama server: `strategy -> script -> quality gate -> composition_agent -> composition_validator -> video_engine (remotion render) -> encode -> platform_adaptor` produced a genuine `.mp4` (1080x1920, 30fps, `ffprobe`-confirmed). Two real bugs surfaced during that run, not code review, and were fixed:
1. `subprocess.run(["npx", ...])` fails outright on Windows with `WinError 2` — `npx`/`npm` are `.cmd` shims, not directly-executable binaries. Fixed by resolving the binary via `shutil.which()` first.
2. `encode.py`'s default `h264_nvenc` failed on this machine's driver (nvenc API 13.1 required, 13.0 found). Default changed to `libx264` (software, no driver dependency) — see `app/config/settings.py`.

The composition retry-then-fall-through behaved as designed on that same run: the LLM's `Outro` text exceeded the character cap twice in a row, `composition_agent` was retried its full `MAX_QUALITY_RETRIES` times, and the orchestrator correctly rendered anyway rather than looping. Worth revisiting the prompt if this shows up often in practice.

## License note

Remotion's license requires a paid company license past a small-team size, which sits in tension with this project's "keep the stack free and open source" goal (see README). Worth checking remotion.dev/license against your actual usage.

## Privacy note

Nothing leaves the machine — Remotion renders entirely via a local headless-Chromium subprocess.

## Frame interpolation and audio

No frame interpolation step exists any more (RIFE was removed along with the diffusion paths it served). FFmpeg multiplexes the narration/audio track and encodes the final H.264 output directly from Remotion's output.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
