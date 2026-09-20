# Local Diffusion Model Options

> **Superseded.** The local diffusion path (and the remote Wan2.1 dispatch path it motivated) was removed from the pipeline in favor of Remotion (code-driven rendering, no diffusion model) once that path was confirmed reliably working — see [[03 Workflow/03 Video Rendering Path]]. Kept as the design record for why: the findings below are real, measured results, not guesses.

This note captures the practical choices for running local diffusion within the 4GB VRAM budget.

## Allowed

### 1. SD1.5 (base)

- the reference model for both the poster background pass and the AnimateDiff motion module
- runs at fp16 under ~2.5GB VRAM at moderate resolution

### 2. SD1.5 LCM / Turbo derivatives

- fewer inference steps for faster turnaround on constrained hardware
- same VRAM envelope as base SD1.5

### 3. AnimateDiff (on top of SD1.5) — validated NOT VIABLE on this hardware

Measured directly on the target 1050 Ti (2026-09-18), using `app/media/video_engine.py:render_local`, default resolution, 20 steps. Three configurations, none genuinely fit:

| Config | Frames | Result |
| --- | --- | --- |
| attention slicing only, `.to("cuda")` | 16 | `torch.OutOfMemoryError` on the first denoising step. 6.3GB already allocated against a 4GB card — off by more than 2x. |
| + `unet.enable_forward_chunking()` + `enable_model_cpu_offload()` | 16 | No CUDA OOM, but ~71-75s/step (~25 min total) and **segfaulted** at the last step — almost certainly system RAM exhaustion (offloading trades VRAM pressure for RAM pressure; this machine only has 8GB total, see [[06 Operations/03 Hardware Constraints]]). |
| attention slicing + forward chunking, `.to("cuda")` | 4 | "Completed" (exit 0) but peak allocated was still **6.7GB** — essentially unchanged from the 16-frame run — at **~150s/step (~55 min total)**. This is almost certainly Windows' CUDA-to-system-memory fallback silently covering the gap, not the workload actually fitting in VRAM. Not a real pass. |

Conclusion: the fixed overhead of SD1.5 + the AnimateDiff motion module already exceeds 4GB under attention slicing regardless of frame count (4 vs 16 barely changed peak allocation) — frame count was never the dominant variable. `enable_model_cpu_offload()` is the only strategy that fails cleanly (a catchable exception) rather than crashing outright or silently overflowing into unusably slow territory, but it isn't confirmed safe either given the RAM segfault at 16 frames. **Do not treat the local AnimateDiff path as viable without a real fix** (a smaller/quantized checkpoint, much lower resolution, or accepting the segfault risk at a frame count small enough to fit in the RAM budget - untested).

## Prohibited

### SDXL and larger checkpoints

- routinely need more VRAM than this card has, even before any motion module or LoRA is added
- not permitted as a local path under any configuration

## Open questions to validate

- whether `enable_model_cpu_offload()` at a very low frame count (2-4) avoids both the VRAM OOM and the RAM segfault - untested
- whether a fundamentally different local video approach (e.g. a smaller/distilled motion model, or dropping AnimateDiff for interpolation-only motion) is a better use of effort than continuing to tune AnimateDiff on this exact card

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/02 Tool Comparison]]
