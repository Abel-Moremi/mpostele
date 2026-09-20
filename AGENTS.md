# AGENTS.md

## Mission

This repository is a local-first pipeline for generating autonomous marketing videos and posters using an LLM agent swarm plus code-driven rendering (Revideo, via headless Chromium) — no diffusion model, no GPU dependency. The core principle is the **Sequential Execution Contract**: every stage, LLM call or render, runs as a transient, single-responsibility subprocess.

The agent working in this repo should favor correctness and reliability over chasing higher-fidelity generative output.

## Project intent

- Generate both short-form video and high-resolution static posters from the same strategy/script agent swarm
- Run the LLM planning layer (`Qwen2.5-1.5B` via Ollama) and the Revideo render stage without either being resident at the same time
- Keep rendering deterministic: a small, hand-written library of scene generators in `revideo/src/`, driven only by agent-generated *data* (which components, what text, what timing) — never agent-generated scene code
- Keep the workflow reproducible and debuggable via a single `state.json` per job

## Non-negotiable constraints

- Every generation step (LLM call, Revideo render, encode) runs in its own subprocess via `subprocess.run` — never imported into one long-lived process
- Explicit unload hook (`keep_alive: 0` for Ollama) runs before rendering starts, not assumed away by process exit alone
- Agent output that drives a render is always validated by a deterministic checker (`quality_inspector.py`, `composition_validator.py`, `poster_validator.py`) before a render subprocess is spawned — never trust LLM JSON output directly
- Quality/composition/poster gate retries are capped at `MAX_QUALITY_RETRIES` (2); after that, fall through and render anyway rather than looping forever
- Intermediate frames and temp files are purged on job completion — only final artifacts persist

## Preferred technical direction

Use these as the default pattern unless a task clearly requires otherwise:

1. Strategy/script/composition/layout planning via the Ollama agent swarm, one prompt per subprocess call
2. Video and poster rendering via the `revideo/` Node project (`node render.mjs --project video` / `--project poster`), never a diffusion model
3. FFmpeg for the final audio multiplexing and encode pass (video only)
4. All cross-stage state read from and appended to `state.json` — no in-memory hand-off between stages

## Architecture guidance

The repository is organized around a branching production flow:

- agent swarm plans strategy and script
- Ollama model is explicitly unloaded before rendering begins
- pipeline branches by `media_type`: poster (`poster_layout_agent` → `poster_validator` → `poster_engine`'s Revideo poster render) or video (`composition_agent` → `composition_validator` → `video_engine`'s Revideo video render → `encode`)
- platform adaptor formats output captions per target platform
- final artifacts are flushed to disk and intermediates are cleaned up

The agent should assume every stage boundary is also a process-isolation boundary.

## Code and implementation preferences

- Prefer small, clear modules over broad abstractions
- Keep configuration explicit and local
- When adding a feature, ask whether it can be spawned and killed as its own subprocess
- Keep assets and generated media in structured, cleaned-up folders
- Never let an agent generate render code (scene/Python compositing logic) — only data that flows into hand-written, reused components

## Project-specific guardrails

- Do not add a persistent worker daemon, resident model server, or long-lived render process as a default path
- Do not reintroduce a diffusion model (local or remote) without a clear reason the Revideo path can't cover — it was removed after being confirmed less reliable (driver/VRAM/network dependent) than code-driven rendering
- Do not skip the deterministic validation gate before a render is spawned, even for a "simple" agent output shape
- Do not add large dependencies without a clear reason — the whole point of this pipeline is staying small and dependency-light

## Recommended repo patterns

- Use documentation files under docs-mpostele for design decisions and architecture notes
- Keep root-level files focused and readable
- Treat README.md as the high-level overview for humans
- Treat docs-mpostele as the operational and design record — including a note on paths that were tried and abandoned, not just what shipped
- When building features, preserve the transient-subprocess, data-not-code narrative of the project

## When making changes

Before implementing a feature or fix, the agent should check:

- Does this stage run and die as its own subprocess?
- Is agent-generated output validated by a deterministic gate before it drives a render?
- Is state read from and written back to `state.json` rather than held in memory across stages?
- Does the change keep rendering code-driven (hand-written components + agent data), not agent-generated code?

If a proposed change fails those checks, the agent should suggest a simpler or more isolated alternative.

## Communication style for future agents

- Be concise and practical
- Explain tradeoffs plainly
- Prefer evidence-based recommendations over assumed feasibility
- Keep implementation aligned with the repo's purpose
- Suggest the simplest viable path first

## Suggested next directions

Good directions for this repo include:

- the orchestrator's subprocess lifecycle and state.json read/write contract
- the Ollama agent swarm (prompt templates, retry/quality-gate loops)
- the Revideo scene library and its data contract with the Python agents
- RIFE-free, direct FFmpeg encode/mux integration
- expanding the fixed component library (more scene types) without letting agents generate code

Less suitable directions include:

- reintroducing a diffusion model or GPU dependency
- a persistent model server or always-on render process
- abstractions that hide subprocess boundaries or hand-off state in memory instead of via `state.json`
- letting an agent generate render code directly instead of data for a fixed component

## Final rule

This repo is best understood as a pragmatic, code-driven AI production pipeline. The agent should always choose the path that preserves the Sequential Execution Contract: transient, isolated, deterministic rendering driven by validated agent data.
