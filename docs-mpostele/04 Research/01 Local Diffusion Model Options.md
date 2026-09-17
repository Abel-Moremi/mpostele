# Local Diffusion Model Options

This note captures the practical choices for running local diffusion within the 4GB VRAM budget.

## Allowed

### 1. SD1.5 (base)

- the reference model for both the poster background pass and the AnimateDiff motion module
- runs at fp16 under ~2.5GB VRAM at moderate resolution

### 2. SD1.5 LCM / Turbo derivatives

- fewer inference steps for faster turnaround on constrained hardware
- same VRAM envelope as base SD1.5

### 3. AnimateDiff (on top of SD1.5)

- adds a motion module on top of the base checkpoint — meaningful additional VRAM overhead, not free
- viable locally only at low frame counts and modest resolution
- **not yet validated on this exact card** — treat frame-count/resolution limits as a hypothesis until measured

## Prohibited

### SDXL and larger checkpoints

- routinely need more VRAM than this card has, even before any motion module or LoRA is added
- not permitted as a local path under any configuration

## Open questions to validate

- whether `--lowvram`-equivalent settings (attention slicing, sequential CPU offload, fp16 VAE) are required in addition to low frame counts for AnimateDiff to stay under 4GB
- actual achievable frame count/resolution combination before OOM, measured on the target 1050 Ti

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/02 Tool Comparison]]
