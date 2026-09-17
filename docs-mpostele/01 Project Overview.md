# Project Overview

mpostele is a local, open-source autonomous content studio for generating short-form marketing videos and high-resolution static posters from a single strategy brief, using an LLM agent swarm plus diffusion-based generation.

## Objective

Build a pipeline that runs a full AI production flow — planning, prompting, quality checking, image/video synthesis, and platform adaptation — on a modest laptop, by treating every generative step as a disposable process rather than a resident service.

## Design constraints

- GTX 1050 Ti with 4GB VRAM
- 8GB system RAM
- offline-first for the LLM and poster paths; the primary video path may dispatch remotely
- open-source tools only
- every generative stage is a transient subprocess with an explicit unload hook before the next stage starts

## Primary approach

The system uses a sequential production flow with a branch by media type:

1. run the agent swarm (strategy → script → keyframe prompt → quality check) via Ollama
2. unload the LLM from RAM before any GPU-heavy stage
3. branch: poster path (SD1.5 background + Pillow compositor) or video path (SD1.5 + AnimateDiff locally, or Wan2.1 dispatched remotely)
4. adapt the output copy per target platform
5. flush final artifacts to disk and purge intermediates

## Why sequential, transient execution instead of persistent services

Continuous background microservices, resident LLM instances, and persistent diffusion pipelines are the primary failure mode on this hardware — they accumulate VRAM/RAM state across jobs until a `CUDA Out Of Memory` error or OS swap thrashing takes the machine down. Instead of avoiding generative models, this project isolates them:

- Ollama's `Qwen2.5-1.5B` is unloaded (`keep_alive: 0`) before any diffusion stage runs
- each diffusion or interpolation pass runs as its own subprocess, so process exit reclaims VRAM even if an in-process flush is missed
- local diffusion is hard-capped to SD1.5-class models; anything heavier (Wan2.1) is dispatched to a remote runtime instead of loaded locally

## Project outcome

The target is a repeatable pipeline that can produce:

- high-resolution marketing posters with structured text/badge layout
- short-form product or campaign videos
- platform-adapted captions for TikTok, Instagram, X, and LinkedIn
- vertical and square exports depending on target platform

## Related notes

- [[02 Architecture]]
- [[06 Operations/03 Hardware Constraints]]
