# Hardware Constraints

## Target environment

The project no longer has a hard hardware budget to design around — it originally targeted a GTX 1050 Ti (4GB VRAM) / 8GB RAM machine because it ran local diffusion models. Since the diffusion stack was removed in favor of Remotion, the pipeline has no GPU or VRAM dependency at all. See [[04 Research/01 Local Diffusion Model Options]] for that history.

## What actually matters now

- Ollama running `Qwen2.5-1.5B` (modest RAM footprint, no GPU required)
- Node.js + a headless-Chromium render process per Remotion job (moderate CPU/RAM during a render, no GPU)
- no persistent worker daemons or resident model servers beyond the Ollama server itself
- every generative or render stage still runs as its own subprocess, so nothing accumulates state across jobs

## The one real constraint left: licensing, not hardware

Remotion's license requires a paid company license past a small-team size (see remotion.dev/license) — worth checking against your intended usage before relying on this pipeline beyond personal/small-scale use, since it sits in tension with the project's "keep the stack free and open source" goal.

## Design principle

The project is still optimized for reliability through process isolation and explicit memory unloading — that discipline outlived the specific hardware constraint that originally motivated it.

## Related notes

- [[01 Project Overview]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[06 Operations/02 Troubleshooting]]
