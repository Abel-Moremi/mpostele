# Video Rendering Path

This stage produces the short-form video from the `keyframe_prompt` and Motion Director output.

## Local rendering engine (fallback)

- SD1.5 + AnimateDiff, intended to be capped at low frame counts to fit the 4GB VRAM budget
- offline, no data leaves the machine
- **measured on the target 1050 Ti: not confirmed viable at any frame count tried (4 or 16)** — every configuration either OOMs, segfaults, or silently overflows into unusably slow system-memory fallback (~150s/step). See [[04 Research/01 Local Diffusion Model Options]] for the full comparison. This is why the remote path below is the primary one, not just a fallback-of-convenience — right now it's closer to the *only* working video path.

## Remote dispatch engine (primary) — implemented against Colab

- Colab has **no official job-submission API** — it's an interactive notebook product, not a queue. The working pattern: [colab/wan21_server.ipynb](../../colab/wan21_server.ipynb) runs a small FastAPI server inside a manually-started Colab session, exposed publicly via ngrok. A human has to open that notebook and press Run each session; nothing on the local side can start it.
- `app/media/video_engine.py:render_remote()` is the local HTTP client: `POST {endpoint}/generate` → poll `GET {endpoint}/status/{job_id}` → `GET {endpoint}/result/{job_id}` to download the finished `.mp4`. Every request carries an `x-api-key` header (`WAN21_API_KEY`) that must match the notebook's `API_KEY` cell — an unauthenticated public ngrok URL would let anyone who finds it submit jobs to your GPU or pull down your output.
- The notebook processes one job at a time (a single background worker thread + queue) — matches the Sequential Execution Contract and avoids two concurrent Wan2.1 generations fighting over Colab's GPU.
- **privacy tradeoff:** this path sends prompts (and eventually source images, once image-to-video is wired up) to a Colab session — if a job must stay fully local, force the fallback path instead.
- **confirmed working end to end (2026-09-18)** against a live Colab T4 session: submit → poll → download produced a genuine, verified H.264 `.mp4` (320x576, 16fps, 9 frames, 0.5625s — `ffprobe`-confirmed). Getting there took five iterations, each a real measured failure, not a guess:
  1. `WanPipeline(...).to("cuda")`, no optimizations, 33 frames/480x832 → **crashed the whole Colab kernel** (system RAM exhaustion, per Colab's own resource panel - Jupyter's `AsyncIOLoopKernelRestarter` auto-restarted it, confirming a hard process crash, not a catchable exception). Root cause: Wan2.1's text encoder is UMT5-XXL (~4.7B params, ~9.4GB in bf16) - roughly 3.5x the 1.3B transformer itself.
  2. `enable_model_cpu_offload()` (17 frames/320x576) → **crashed again** - offloading keeps everything resident in system RAM by design, which is backwards when the actual bottleneck is RAM, not VRAM.
  3. `device_map="cuda"` (direct GPU load) → no crash, but a clean `torch.OutOfMemoryError` 594MB short of the T4's ~14.56GB VRAM, during attention.
  4. Added `enable_attention_slicing()`, dropped to 9 frames → the weights alone (~13.5GB) now OOM'd mid-*load*, before generation even started - "cuda" doesn't leave enough headroom for the full model.
  5. `device_map="balanced"` (splits the model across GPU + free system RAM automatically) → loading and the full denoising loop succeeded, but decode-time OOM'd inside the VAE's `conv3d`.
  6. Added `vae.enable_slicing()` + `vae.enable_tiling()` → **succeeded.**
- The client's polling loop needed two robustness fixes along the way: retrying through transient `ConnectionError`/`Timeout` (the tunnel drops connections while the worker thread is busy loading/running the model) and through `HTTPError` on a 502/503/504 (which `raise_for_status()` raises separately from connection-level errors).
- The HTTP client logic itself (submit/poll/download/auth) is also verified against a fake local server in `scripts/smoke_test_remote_dispatch.py`.
- **Not yet tried:** raising frame count/resolution above this confirmed-working floor (9 frames, 320x576). Increase incrementally and re-verify - nothing here suggests headroom scales linearly.

## Remotion rendering engine (opt-in, code-driven, no diffusion model)

- Selected only via explicit `--execution-mode remotion` — never chosen by `dispatcher.py`'s local/remote auto-fallback, so the existing two paths keep working standalone regardless of whether Node/Remotion is installed.
- No AI-generated motion at all: a `composition_agent` (Ollama, `app/agents/composition_agent.py`) produces a *data* spec — an ordered list of scenes, each naming one of three fixed components (`TitleReveal`, `CaptionOverlay`, `Outro`) plus duration and text/color props — never JSX. The scene components themselves are hand-written once in `remotion/src/scenes/` and reused across every job, following Remotion's stated best practices: `useCurrentFrame`/`interpolate`/`spring` only (never CSS `@keyframes`, which desyncs under headless frame-by-frame capture), `<Series>`/`<Sequence>` for scene timing.
- `app/agents/composition_validator.py` is a deterministic gate (same shape as `quality_inspector.py`) that checks the spec's component names, prop completeness, and text/duration limits *before* a render is spawned — `remotion/src/schema.ts`'s Zod schema is the second half of that validation boundary, on the Node side.
- `app/media/remotion_engine.py` shells out to `npx remotion render` inside the sibling `remotion/` Node project (the repo's first non-Python toolchain — needs `cd remotion && npm install` once, see the Setup Checklist). Output lands straight in `artifacts.interpolated_clip`, skipping the RIFE `INTERPOLATION` stage entirely — Remotion renders natively at its target FPS, so there's no low-frame-count generative source to upsample the way AnimateDiff/Wan2.1 output needs.
- **Confirmed working (2026-09-19)**, with one caveat: `npm install` in `remotion/`, a standalone `npx remotion render`, and `remotion_engine.render()` called directly with a realistic `composition_spec` all produced a valid `.mp4` (`ffprobe`-confirmed 1080x1920, 30fps, frame count matching the scene durations summed). One real bug surfaced and was fixed in the process — `subprocess.run(["npx", ...])` fails outright on Windows with `WinError 2` because `npx`/`npm` are `.cmd` shims, not directly-executable binaries; `remotion_engine.py` now resolves the binary via `shutil.which()` first. **Not yet exercised**: the `composition_agent` LLM step itself (needs a live Ollama server, same bar as the rest of the agent swarm) and the full orchestrator path end to end (`--execution-mode remotion` through to `PLATFORM_ADAPTOR`).
- **License note:** Remotion's license requires a paid company license past a small-team size, which sits in tension with this project's "keep the stack free and open source" goal (see README). Worth checking remotion.dev/license against your actual usage before relying on this path beyond personal/small-scale use.
- **Privacy note:** unlike the Wan2.1 path, nothing leaves the machine here — Remotion renders entirely via a local headless-Chromium subprocess.

## Frame interpolation and audio

- RIFE interpolates from the native generation frame rate (commonly 16 FPS) up to 32 or 60 FPS
- FFmpeg multiplexes the narration/audio track and encodes the final H.264 output

## Open question

The local fallback is unconfirmed at any tested frame count - see [[04 Research/01 Local Diffusion Model Options]] for the three failure modes measured so far. Getting it to genuinely work would need a real fix (lower resolution, a smaller checkpoint) rather than just tuning frame count further, and even then the pace observed (70-150s/step) may make it impractical for a "short-form" pipeline regardless. The remote path is now confirmed working, so this is no longer a hard blocker on the video path overall - just an open question about whether the local fallback is worth continuing to invest in.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
