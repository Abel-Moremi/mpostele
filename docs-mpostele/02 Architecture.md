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
      ├──► [ Poster Path ] ──► Local SD1.5 background + Pillow compositor
      │
      └──► [ Video Path ]  ──► Local SD1.5 + AnimateDiff (fallback)
                               OR Remote Wan2.1 dispatch (primary)
```

## Components

### 1. Orchestrator Engine

Controls pipeline execution, state machine progression, error recovery, and process termination. Spawns each phase as an independent OS-level subprocess, and forcefully signals model unloads and CUDA cache flushes before launching the next one.

### 2. Agent Pipeline Swarm

`Qwen2.5-1.5B` via Ollama, executing task-specific prompts sequentially: Strategy & Trend, Script & Layout, Keyframe Prompt, Motion Director, Poster Composition, Quality Inspector, Platform Adaptor, and the Execution Dispatcher. The orchestrator unloads the model from RAM before any image or video generation process is spawned. See [[03 Workflow/01 Agent Pipeline Swarm]].

### 3. Poster Rendering Engine

A local SD1.5 (or LCM/Turbo derivative) generates a text-free background under ~2.5GB VRAM. Pillow composites text, badges, and logos on top using bounding-box-aware word wrapping. See [[03 Workflow/02 Poster Rendering Path]].

### 4. Video Processing Engine

SD1.5 + AnimateDiff renders locally at low frame counts as the fallback path; Wan2.1 is dispatched to a remote runtime (Colab/Modal/RunPod) as the primary, higher-fidelity path. RIFE interpolates frames and FFmpeg handles audio multiplexing and H.264 encoding. See [[03 Workflow/03 Video Rendering Path]].

## Practical fit

This architecture matches the hardware constraints not by avoiding diffusion models, but by never letting more than one generative stage hold GPU/RAM state at a time — every stage boundary is also a memory-reset boundary, enforced by subprocess isolation plus explicit unload hooks.

## Related notes

- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[03 Workflow/05 Platform Adaptation & Export]]
