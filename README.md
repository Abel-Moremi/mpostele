# mpostele

mpostele is a local-first, autonomous content studio for generating **short-form marketing videos** and **high-resolution static posters** entirely on resource-constrained developer hardware.

This project is designed around a real hardware constraint: a GTX 1050 Ti with 4GB VRAM and 8GB system RAM. The goal is to run a full AI production pipeline — LLM planning agents plus diffusion-based image and video generation — without exceeding that budget, by treating every generation step as a disposable process instead of a resident service.

## Why this project exists

Continuous background microservices, resident LLM instances, and persistent diffusion pipelines will crash this hardware profile via `CUDA Out Of Memory` errors or OS swap thrashing. Instead of avoiding generative models outright, mpostele constrains *how* they run:

- every pipeline stage executes as a **transient, single-responsibility subprocess**
- models are explicitly unloaded (`keep_alive: 0`, CUDA cache flush) before the next stage starts
- local diffusion is hard-capped to SD1.5-class models — no SDXL, no resident checkpoints
- heavier video fidelity is offloaded to a remote dispatch target rather than forced onto 4GB of VRAM

## Architecture overview

```text
                 ┌───────────────────────────┐
                 │   CLI / Web Portal         │
                 └─────────────┬───────────────┘
                               ▼
                 ┌───────────────────────────┐
                 │   Orchestrator Engine      │
                 └─────────────┬───────────────┘
                               │
           ┌───────────────────┴───────────────────┐
           ▼                                       ▼
┌───────────────────────────┐           ┌───────────────────────────┐
│  Agent Pipeline Swarm      │           │  Local State Manager       │
│  (transient subprocesses)  │◄─────────►│  (state.json on disk)      │
└─────────────┬───────────────┘           └───────────────────────────┘
              │
              ├───► [ Video Path ]  ──► Local SD1.5 + AnimateDiff (fallback) OR Remote Wan2.1 dispatch (primary) OR Remotion code-driven render (opt-in)
              │
              └───► [ Poster Path ] ──► Local SD1.5 background + Pillow vector compositor
```

## Pipeline stages

1. **Agent swarm** (`Qwen2.5-1.5B` via Ollama) — strategy, script, keyframe prompts, motion direction, poster layout, quality inspection, and platform adaptation, run sequentially and unloaded from RAM before any GPU-heavy stage starts.
2. **Poster path** — a text-free SD1.5 background under ~2.5GB VRAM, composited with Pillow for text, badges, and logos using bounding-box-aware word wrapping.
3. **Video path** — SD1.5 + AnimateDiff locally at low frame counts as a fallback, or a remote-dispatched Wan2.1 (1.3B/14B) job as the primary path for higher-fidelity output, followed by RIFE frame interpolation and FFmpeg audio/encode. A third, opt-in path renders via Remotion (Node/React, headless Chromium) — code-driven motion graphics from a fixed scene library, no diffusion model or VRAM use at all; see [docs-mpostele/03 Workflow/03 Video Rendering Path](docs-mpostele/03%20Workflow/03%20Video%20Rendering%20Path.md) for the license caveat before relying on it.
4. **Platform adaptation** — reformats scripts and captions per target platform (TikTok, Instagram, X, LinkedIn).

See [docs-mpostele/00 Home](docs-mpostele/00%20Home.md) for the full design vault.

## A privacy note

Most of this pipeline is fully local. The one exception: the **primary** video path dispatches to a remote runtime (Google Colab, Modal, RunPod) to run Wan2.1, since that model doesn't fit in 4GB of VRAM. If a job needs to stay entirely on-device, use the local SD1.5 + AnimateDiff fallback path instead — it trades fidelity and frame count for staying offline.

## Directory structure

```text
mpostele/
├── app/
│   ├── main.py              # CLI entry point
│   ├── cli.py               # shared --job arg parsing for every stage
│   ├── config/
│   │   └── settings.py      # VRAM/model/path config, all env-overridable
│   ├── orchestrator/
│   │   ├── state.py             # state.json read/append contract
│   │   ├── process_runner.py    # spawns each stage as its own subprocess
│   │   └── orchestrator.py      # the sequential control flow + quality gate
│   ├── agents/               # Ollama-backed swarm, one module per agent
│   │   ├── base.py              # call_ollama() + JSON extraction
│   │   ├── strategy_agent.py
│   │   ├── script_agent.py
│   │   ├── keyframe_agent.py
│   │   ├── motion_agent.py            # local/remote video targets only
│   │   ├── composition_agent.py       # remotion video target only - scene list, not JSX
│   │   ├── composition_validator.py   # remotion video target only - deterministic gate
│   │   ├── poster_layout_agent.py     # poster path only
│   │   ├── quality_inspector.py
│   │   ├── platform_adaptor.py
│   │   └── dispatcher.py
│   └── media/
│       ├── memory.py            # unload_ollama_model / flush_cuda_memory
│       ├── compositor.py        # Pillow text/badge compositor
│       ├── poster_engine.py     # SD1.5 background + Pillow compositor
│       ├── video_engine.py      # AnimateDiff local / Wan2.1 remote dispatch
│       ├── remotion_engine.py   # shells out to the remotion/ Node project
│       ├── interpolation.py     # RIFE
│       ├── encode.py            # FFmpeg audio mux + final encode
│       └── assets/
│           ├── jobs/     # one state.json per job (gitignored)
│           ├── tmp/      # intermediate frames, purged on completion
│           ├── output/   # final posters/videos
│           └── fonts/    # .ttf files - not bundled, add your own
├── examples/
│   └── sample_brief.json
├── remotion/              # Node/React project for --execution-mode remotion (optional)
│   └── src/
│       ├── index.ts
│       ├── Root.tsx           # composition registration + Zod schema + calculateMetadata
│       ├── schema.ts          # Zod schema, mirrors composition_validator.py's shape
│       ├── MainComposition.tsx  # data-driven <Series>, the only place component names resolve to code
│       └── scenes/            # fixed, hand-written scene components (TitleReveal, CaptionOverlay, Outro)
├── requirements.txt
├── README.md
├── LICENSE
└── docs-mpostele/
```

## Quickstart

```bash
pip install -r requirements.txt
ollama pull qwen2.5:1.5b && ollama serve &
python -m app.main --media-type poster --brief-file examples/sample_brief.json
```

This is a scaffold, not a finished pipeline: the local AnimateDiff path and the
remote Wan2.1 dispatch client are stubbed (see `app/media/video_engine.py`),
and font files for the Pillow compositor aren't bundled — see
[docs-mpostele/05 Implementation/03 Setup Checklist](docs-mpostele/05%20Implementation/03%20Setup%20Checklist.md).

## Project goals

- run a full LLM + diffusion production pipeline locally on a 4GB VRAM / 8GB RAM machine
- keep every generation stage transient and explicitly memory-unloaded
- cap local diffusion at SD1.5-class models; dispatch remotely for anything heavier
- produce both short-form video and high-resolution poster output from the same agent swarm
- keep the stack free and open source

## Summary

This repo is built around a sequential execution contract: an LLM agent swarm plans the content, then hands off to a diffusion-based poster or video engine, with strict process isolation and memory-unload hooks between every stage. It favors correctness under a fixed memory budget over raw model capability.
