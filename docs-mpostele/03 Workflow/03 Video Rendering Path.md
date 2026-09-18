# Video Rendering Path

This stage produces the short-form video from the `keyframe_prompt` and Motion Director output.

## Local rendering engine (fallback)

- SD1.5 + AnimateDiff, capped at low frame counts to fit the 4GB VRAM budget
- offline, no data leaves the machine
- fidelity and frame count are intentionally limited — this is the fallback path, not the default
- **measured on the target 1050 Ti: not viable at 16 frames under either tried strategy** — see [[04 Research/01 Local Diffusion Model Options]]. This reinforces why the remote path below is the primary one, not just a fallback-of-convenience.

## Remote dispatch engine (primary)

- routes high-fidelity Wan2.1 (1.3B/14B) text-to-video / image-to-video payloads to a remote runtime (Google Colab, Modal, RunPod)
- used by default for anything beyond what the local fallback can produce
- **privacy tradeoff:** this path sends prompts and/or source images off-device — if a job must stay fully local, force the fallback path instead

## Frame interpolation and audio

- RIFE interpolates from the native generation frame rate (commonly 16 FPS) up to 32 or 60 FPS
- FFmpeg multiplexes the narration/audio track and encodes the final H.264 output

## Open question

16 frames is confirmed too many for this hardware (see [[04 Research/01 Local Diffusion Model Options]] for the measured failure modes). Whether a lower frame count (4-8) fits within budget, and whether the resulting generation speed (~70s/step under CPU offloading) is even useful for a short-form pipeline, is still open.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/03 FFmpeg Notes]]
