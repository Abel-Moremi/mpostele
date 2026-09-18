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
- **first live attempt (2026-09-18) crashed the Colab kernel outright** — `WanPipeline(...).to("cuda")` with no memory optimizations, 33 frames at 480x832, killed the whole process (Jupyter's `AsyncIOLoopKernelRestarter` auto-restarted it — the same "hard crash, not a catchable exception" failure mode as the local AnimateDiff segfault). The client's polling loop also didn't tolerate the transient connection drop that preceded it - fixed to retry through `ConnectionError`/`Timeout` within the overall deadline. Second attempt: `enable_model_cpu_offload()` added to the notebook, frame count/resolution dropped to 17 / 320x576 for a smaller first test. Result of that attempt not yet known.
- the HTTP client logic itself (submit/poll/download/auth, including the retry-on-transient-drop path) is separately verified against a fake local server in `scripts/smoke_test_remote_dispatch.py`.

## Frame interpolation and audio

- RIFE interpolates from the native generation frame rate (commonly 16 FPS) up to 32 or 60 FPS
- FFmpeg multiplexes the narration/audio track and encodes the final H.264 output

## Open question

The local fallback is unconfirmed at any tested frame count - see [[04 Research/01 Local Diffusion Model Options]] for the three failure modes measured so far. Getting it to genuinely work would need a real fix (lower resolution, a smaller checkpoint) rather than just tuning frame count further, and even then the pace observed (70-150s/step) may make it impractical for a "short-form" pipeline regardless. Until that's resolved, treat the remote Wan2.1 path as load-bearing, not optional.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
