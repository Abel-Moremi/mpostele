# Hardware Constraints

## Target environment

The project no longer has a hard hardware budget to design around — it originally targeted a GTX 1050 Ti (4GB VRAM) / 8GB RAM machine because it ran local diffusion models. Since the diffusion stack was removed in favor of code-driven rendering (Remotion, then Revideo), the pipeline has no GPU or VRAM dependency at all. See [[04 Research/01 Local Diffusion Model Options]] for that history.

## What actually matters now

- Ollama running `Qwen2.5-1.5B` (modest RAM footprint, no GPU required)
- Node.js + a headless-Chromium render process per Revideo job (moderate CPU/RAM during a render, no GPU)
- no persistent worker daemons or resident model servers beyond the Ollama server itself
- every generative or render stage still runs as its own subprocess, so nothing accumulates state across jobs

## Licensing constraint: resolved, not just noted

Remotion (the original renderer) required a paid company license past a small-team size, in tension with the project's "keep the stack free and open source" goal. That's why it was swapped for Revideo, which is MIT-licensed across every package it depends on — see [[07 Reference/02 Notes Archive]] for the swap rationale. No licensing caveat applies to this pipeline any more.

## Design principle

The project is still optimized for reliability through process isolation and explicit memory unloading — that discipline outlived the specific hardware constraint that originally motivated it.

## Related notes

- [[01 Project Overview]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/01 Local Diffusion Model Options]]
- [[06 Operations/02 Troubleshooting]]
