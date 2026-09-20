# mpostele

This vault is the knowledge base for a local-first autonomous content studio: an LLM agent swarm plus code-driven rendering (Remotion), run under a Sequential Execution Contract.

## Core idea

The project generates both short-form marketing video and high-resolution static posters from the same planning layer. Rendering is deterministic and code-driven, not model inference:

- `Qwen2.5-1.5B` via Ollama for strategy, script, and per-media-type composition planning
- Remotion (headless Chromium) renders both paths — `npx remotion still` for posters, `npx remotion render` for video — from a small, hand-written component library
- every stage is a transient subprocess with an explicit unload hook before the next one starts

This replaced an earlier local-diffusion-based design (SD1.5, AnimateDiff, remote Wan2.1 dispatch) once the Remotion path proved more reliable in practice — see [[04 Research/01 Local Diffusion Model Options]] for that history.

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

Rather than running resident LLM/render services, the project isolates every generative step into its own disposable process with an explicit memory-unload hook, so no single job can accumulate resident state across runs.
