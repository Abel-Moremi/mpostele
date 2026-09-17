# Hardware Constraints

## Target environment

- GTX 1050 Ti with 4GB VRAM
- 8GB system RAM
- local-first; the primary video path may dispatch to a remote runtime

## Implications

- no persistent worker daemons or resident model servers beyond the Ollama server itself
- every generative stage runs as its own subprocess with an explicit unload hook before the next stage starts
- local diffusion is hard-capped to SD1.5-class models — SDXL is prohibited locally under any configuration
- AnimateDiff's real VRAM ceiling on this exact card is not yet validated — treat "low frame count" as a hypothesis until measured
- heavier video fidelity is handled by remote Wan2.1 dispatch rather than by relaxing the local VRAM cap

## Design principle

This project is optimized for reliability under a fixed 4GB VRAM / 8GB RAM budget rather than avoiding generative models outright — the constraint is enforced through process isolation and explicit memory unloading, not through excluding diffusion/LLM inference.

## Related notes

- [[01 Project Overview]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[06 Operations/02 Troubleshooting]]
