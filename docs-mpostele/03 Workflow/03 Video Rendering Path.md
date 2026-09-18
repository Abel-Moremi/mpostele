# Video Rendering Path

This stage produces the short-form video from the `keyframe_prompt` and Motion Director output.

## Local rendering engine (fallback)

- SD1.5 + AnimateDiff, intended to be capped at low frame counts to fit the 4GB VRAM budget
- offline, no data leaves the machine
- **measured on the target 1050 Ti: not confirmed viable at any frame count tried (4 or 16)** — every configuration either OOMs, segfaults, or silently overflows into unusably slow system-memory fallback (~150s/step). See [[04 Research/01 Local Diffusion Model Options]] for the full comparison. This is why the remote path below is the primary one, not just a fallback-of-convenience — right now it's closer to the *only* working video path.

## Remote dispatch engine (primary)

- routes high-fidelity Wan2.1 (1.3B/14B) text-to-video / image-to-video payloads to a remote runtime (Google Colab, Modal, RunPod)
- used by default for anything beyond what the local fallback can produce
- **privacy tradeoff:** this path sends prompts and/or source images off-device — if a job must stay fully local, force the fallback path instead

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
