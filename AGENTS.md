# AGENTS.md

## Mission

This repository is a local-first pipeline for generating autonomous marketing videos and posters using an LLM agent swarm plus diffusion-based image/video generation, constrained to run on a GTX 1050 Ti (4GB VRAM) / 8GB RAM machine. The core principle is the **Sequential Execution Contract**: generative models may be used, but only as transient, single-responsibility subprocesses that are explicitly unloaded between stages.

The agent working in this repo should favor correctness under a fixed memory budget over model capability or pipeline throughput.

## Project intent

- Generate both short-form video and high-resolution static posters from the same strategy/script agent swarm
- Run the LLM planning layer (`Qwen2.5-1.5B` via Ollama) and the diffusion layer (SD1.5, AnimateDiff) without either being resident at the same time
- Dispatch remotely (Wan2.1 via Colab/Modal/RunPod) only for the video path, and only when local fidelity isn't sufficient
- Keep the workflow reproducible and debuggable via a single `state.json` per job

## Non-negotiable constraints

- Every generation step (LLM call, diffusion pass, interpolation, encode) runs in its own subprocess via `subprocess.run` — never imported into one long-lived process
- Explicit unload hooks (`keep_alive: 0` for Ollama, `torch.cuda.empty_cache()` + `gc.collect()` inside the dying child) run between phases, not assumed away by process exit alone
- No SDXL or any checkpoint that can't run under ~2.5GB VRAM locally — SD1.5 and its LCM/Turbo derivatives only
- Quality Inspector retries are capped at 2 cycles; after that, fall back to default layout/prompt metrics and proceed rather than looping
- Intermediate frames, raw diffusion dumps, and temp audio are purged on job completion — only final artifacts persist

## Preferred technical direction

Use these as the default pattern unless a task clearly requires otherwise:

1. Strategy/script/prompt/layout planning via the Ollama agent swarm, one prompt per subprocess call
2. Poster backgrounds via local SD1.5, composited with Pillow (bounding-box-aware text wrapping, badges, logos)
3. Video via local SD1.5 + AnimateDiff at low frame counts as the offline fallback, or remote Wan2.1 dispatch as the higher-fidelity primary path
4. RIFE for frame interpolation, FFmpeg for audio multiplexing and final encode
5. All cross-stage state read from and appended to `state.json` — no in-memory hand-off between stages

## Architecture guidance

The repository is organized around a branching production flow:

- agent swarm plans strategy, script, prompts, and layout
- Ollama model is explicitly unloaded before any GPU-heavy stage begins
- pipeline branches by `media_type`: poster (SD1.5 + Pillow) or video (AnimateDiff local / Wan2.1 remote)
- platform adaptor formats output captions per target platform
- final artifacts are flushed to disk and intermediates are cleaned up

The agent should assume every stage boundary is also a memory-reset boundary.

## Code and implementation preferences

- Prefer small, clear modules over broad abstractions
- Keep configuration explicit and local
- Write code that keeps VRAM/RAM usage visible and boundable, not just "eventually garbage collected"
- When adding a feature, ask whether it can be spawned and killed as its own subprocess
- Keep assets and generated media in structured, cleaned-up folders

## Project-specific guardrails

- Do not add a persistent worker daemon, resident model server, or long-lived GPU context as a default path
- Do not load SDXL or any model that doesn't fit the stated VRAM budget locally
- Do not assume the remote dispatch path is available — the local fallback must keep working standalone
- Do not skip the explicit unload hooks between LLM and diffusion phases, even if the process-exit boundary would eventually free the memory anyway
- Do not add large dependencies without checking their VRAM/RAM footprint against the 4GB/8GB budget

## Recommended repo patterns

- Use documentation files under docs-mpostele for design decisions and architecture notes
- Keep root-level files focused and readable
- Treat README.md as the high-level overview for humans
- Treat docs-mpostele as the operational and design record
- When building features, preserve the transient-process, explicit-unload narrative of the project

## When making changes

Before implementing a feature or fix, the agent should check:

- Does this stage run and die as its own subprocess?
- Is there an explicit unload/flush hook before the next memory-heavy stage?
- Does local diffusion usage stay within the SD1.5-class VRAM budget?
- Does the video path still have a working local fallback if remote dispatch is unavailable?
- Is state read from and written back to `state.json` rather than held in memory across stages?

If a proposed change fails those checks, the agent should suggest a simpler or more isolated alternative.

## Communication style for future agents

- Be concise and practical
- Explain tradeoffs plainly, especially VRAM/RAM tradeoffs
- Prefer evidence-based recommendations over assumed feasibility
- Keep implementation aligned with the repo's purpose
- Suggest the simplest viable path first

## Suggested next directions

Good directions for this repo include:

- the orchestrator's subprocess lifecycle and state.json read/write contract
- the Ollama agent swarm (prompt templates, retry/quality-inspector loop)
- the Pillow compositor's bounding-box and word-wrap logic
- validating AnimateDiff's actual VRAM footprint at various frame counts on a 1050 Ti
- the remote dispatch client for Wan2.1 (Colab/Modal/RunPod)
- RIFE interpolation and FFmpeg encode/mux integration

Less suitable directions include:

- a persistent model server or always-on GPU process
- SDXL or other checkpoints that exceed the local VRAM budget
- abstractions that hide subprocess boundaries or hand-off state in memory instead of via `state.json`

## Final rule

This repo is best understood as a pragmatic, memory-bounded AI production pipeline. The agent should always choose the path that preserves the Sequential Execution Contract: transient, isolated, explicitly unloaded, and functional within the stated hardware budget.
