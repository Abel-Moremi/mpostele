# Local Diffusion Model Options

This note captures the practical choices for running local diffusion within the 4GB VRAM budget.

## Allowed

### 1. SD1.5 (base)

- the reference model for both the poster background pass and the AnimateDiff motion module
- runs at fp16 under ~2.5GB VRAM at moderate resolution

### 2. SD1.5 LCM / Turbo derivatives

- fewer inference steps for faster turnaround on constrained hardware
- same VRAM envelope as base SD1.5

### 3. AnimateDiff (on top of SD1.5) — validated not viable at 16 frames

Measured directly on the target 1050 Ti (2026-09-18), using `app/media/video_engine.py:render_local`, default resolution, 16 frames, 20 steps:

- **Attention slicing alone**: `torch.OutOfMemoryError` on the very first denoising step. PyTorch had already allocated 6.3GB against a 4GB card before the crash — not a marginal miss, off by more than 2x.
- **Attention slicing + `unet.enable_forward_chunking()` + `enable_model_cpu_offload()`**: no CUDA OOM, but the run took ~71-75 seconds per step (~25 minutes total) and **segfaulted** at the very last step, most likely from system RAM exhaustion (offloading trades VRAM pressure for RAM pressure, and this machine only has 8GB total — see [[06 Operations/03 Hardware Constraints]]).

Conclusion: 16 frames does not fit this hardware under either strategy tried so far. A much lower frame count (4-8) is the next thing to try before concluding AnimateDiff-local is a dead end outright; it hasn't been tried yet.

## Prohibited

### SDXL and larger checkpoints

- routinely need more VRAM than this card has, even before any motion module or LoRA is added
- not permitted as a local path under any configuration

## Open questions to validate

- whether a much lower frame count (4-8) fits within both the 4GB VRAM and 8GB RAM budgets under `enable_model_cpu_offload()`
- whether the ~70s/step pace (even if it fit) is acceptable for a "short-form" pipeline, or makes the local fallback impractical regardless of whether it technically completes

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/02 Tool Comparison]]
