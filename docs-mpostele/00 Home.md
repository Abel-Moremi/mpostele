# mpostele

This vault is the knowledge base for a local-first autonomous content studio: an LLM agent swarm plus diffusion-based image/video generation, run under a strict Sequential Execution Contract on a GTX 1050 Ti (4GB VRAM) / 8GB RAM machine.

## Core idea

The project generates both short-form marketing video and high-resolution static posters from the same planning layer. Instead of avoiding generative models, it constrains how they run:

- `Qwen2.5-1.5B` via Ollama for strategy, script, prompt, and layout planning
- local SD1.5 for poster backgrounds, composited with Pillow
- local SD1.5 + AnimateDiff as a video fallback, remote Wan2.1 dispatch as the primary video path
- every stage is a transient subprocess with an explicit unload hook before the next one starts

## Workflow

1. [[01 Project Overview]]
2. [[02 Architecture]]
3. [[03 Workflow/01 Agent Pipeline Swarm]]
4. [[03 Workflow/02 Poster Rendering Path]]
5. [[03 Workflow/03 Video Rendering Path]]
6. [[03 Workflow/04 Memory & Process Protocol]]
7. [[03 Workflow/05 Platform Adaptation & Export]]

## Research and decisions

- [[04 Research/01 Local Diffusion Model Options]]
- [[04 Research/02 Tool Comparison]]
- [[04 Research/03 FFmpeg Notes]]
- [[04 Research/04 Pillow Compositor Notes]]
- [[04 Research/05 Ollama Agent Notes]]

## Implementation

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]

## Operations

- [[06 Operations/01 Commands]]
- [[06 Operations/02 Troubleshooting]]
- [[06 Operations/03 Hardware Constraints]]

## Reference

- [[07 Reference/01 Links]]
- [[07 Reference/02 Notes Archive]]

## Why this project exists

The main design constraint is a fixed 4GB VRAM / 8GB RAM budget. Rather than excluding diffusion and LLM inference outright, the project isolates every generative step into its own disposable process with explicit memory-unload hooks, so no single job can accumulate resident state and push the machine into OOM or swap thrashing.
