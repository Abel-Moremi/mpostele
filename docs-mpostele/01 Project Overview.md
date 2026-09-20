# Project Overview

mpostele is a local, open-source autonomous content studio for generating short-form marketing videos and high-resolution static posters from a single strategy brief, using an LLM agent swarm plus code-driven rendering (Revideo).

## Objective

Build a pipeline that runs a full AI production flow — planning, prompting, quality checking, rendering, and platform adaptation — by treating every generative step as a disposable process rather than a resident service.

## Design constraints

- fully local and offline-capable — no diffusion model, no GPU, no remote dispatch dependency
- open-source tools only, genuinely so (MIT-licensed Revideo, not the source-available Remotion it replaced - see [[07 Reference/02 Notes Archive]])
- every generative or render stage is a transient subprocess with an explicit unload hook before the next stage starts
- rendering is code-driven, not model inference: a small, hand-written scene library, driven only by agent-generated data

## Primary approach

The system uses a sequential production flow with a branch by media type:

1. run the agent swarm (strategy → script → quality check) via Ollama
2. unload the LLM from RAM before rendering starts
3. branch: poster path (`poster_layout_agent` → `poster_validator` → Revideo poster render) or video path (`composition_agent` → `composition_validator` → Revideo video render → FFmpeg encode)
4. adapt the output copy per target platform
5. flush final artifacts to disk and purge intermediates

## Why sequential, transient execution instead of persistent services

Continuous background microservices and resident LLM instances are still a failure mode worth avoiding even without a VRAM budget — they accumulate state across jobs and make failures hard to isolate. Every stage is spawned and killed as its own subprocess:

- Ollama's `Qwen2.5-1.5B` is unloaded (`keep_alive: 0`) before rendering runs
- each render pass runs as its own subprocess, so process exit reclaims everything it used
- rendering never falls back to a diffusion model — the whole pipeline was rebuilt around a single, reliable, code-driven path after AnimateDiff/Wan2.1 proved less reliable in practice (see [[04 Research/01 Local Diffusion Model Options]])

## Project outcome

The target is a repeatable pipeline that can produce:

- high-resolution marketing posters with a headline and CTA badge
- short-form product or campaign videos
- platform-adapted captions for TikTok, Instagram, X, and LinkedIn

## Related notes

- [[02 Architecture]]
- [[06 Operations/03 Hardware Constraints]]
