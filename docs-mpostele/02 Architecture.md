# Architecture

## High-level pipeline

```text
             CLI / Web Portal
                    │
                    ▼
            Orchestrator Engine
                    │
      ┌─────────────┴─────────────┐
      ▼                           ▼
Agent Pipeline Swarm   ◄──►  Local State Manager
(transient subprocesses)     (state.json on disk)
      │
      ├──► [ Poster Path ] ──► Revideo poster render (single frame)
      │
      └──► [ Video Path ]  ──► Revideo render (dispatched scenes) ──► FFmpeg encode
```

## Components

### 1. Orchestrator Engine

Controls pipeline execution, state machine progression, error recovery, and process termination. Spawns each phase as an independent OS-level subprocess, and issues the Ollama unload signal before rendering begins.

### 2. Agent Pipeline Swarm

`Qwen2.5-1.5B` via Ollama, executing task-specific prompts sequentially: Strategy & Trend, Script & Layout, Quality Inspector, then a media-type-specific pair — Poster Layout + Poster Validator, or Composition Director + Composition Validator — and Platform Adaptor. The orchestrator unloads the model from RAM before any render process is spawned. See [[03 Workflow/01 Agent Pipeline Swarm]].

### 3. Poster Rendering Engine

`poster_layout_agent` produces a small data spec (headline, CTA text, two colors); `app/media/poster_engine.py` renders it via `node render.mjs --project poster` — a single-frame Revideo scene (`revideo/src/scenes/poster.tsx`). No diffusion model, no separate background/composite step. See [[03 Workflow/02 Poster Rendering Path]].

### 4. Video Processing Engine

`composition_agent` produces a scene list (which fixed component, in what order, for how long, with what text/colors); `app/media/video_engine.py` renders it via `node render.mjs --project video` against `revideo/src/video-project.ts`'s master scene, which dispatches each entry to a hand-written generator. FFmpeg then multiplexes audio and encodes the final H.264 output. No diffusion model, no VRAM dependency, no RIFE interpolation step (Revideo renders natively at its target frame rate). See [[03 Workflow/03 Video Rendering Path]].

## Practical fit

Both render paths are deterministic and code-driven: a small, hand-written library of scene generators in `revideo/src/`, reused across every job, with only the *data* that feeds them coming from the agent swarm — never agent-generated code. That data is always checked by a deterministic validator (`quality_inspector.py`, `composition_validator.py`, `poster_validator.py`) before a render subprocess is spawned. Every stage boundary is still a process-isolation boundary, even without a VRAM budget to manage — subprocess isolation keeps failures contained and state debuggable via `state.json`.

## Related notes

- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[03 Workflow/05 Platform Adaptation & Export]]
