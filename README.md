# mpostele

mpostele is a local-first, autonomous content studio for generating **short-form marketing videos** and **high-resolution static posters**, driven by an LLM planning swarm and rendered entirely through code — no diffusion model, no GPU, no VRAM budget to manage.

The project originally ran local diffusion models (SD1.5, AnimateDiff) under a hard 4GB VRAM / 8GB RAM budget, with a remote Wan2.1 dispatch path for higher fidelity. That whole stack was removed in favor of a single, simpler approach: code-driven rendering via headless Chromium (Revideo, a Node framework) renders both the video and poster paths from data the agent swarm produces. It's the only rendering approach that was ever confirmed reliable without a driver-, VRAM-, or network-dependency to manage — see [docs-mpostele/04 Research/01 Local Diffusion Model Options](docs-mpostele/04%20Research/01%20Local%20Diffusion%20Model%20Options.md) for why the diffusion path was dropped. (Remotion filled this role first; it was later swapped for Revideo over licensing, not reliability — see [docs-mpostele/07 Reference/02 Notes Archive](docs-mpostele/07%20Reference/02%20Notes%20Archive.md).)

## Why this project exists

Continuous background microservices and resident LLM instances still aren't free — the design keeps every generation step disposable rather than resident:

- every pipeline stage executes as a **transient, single-responsibility subprocess**
- the Ollama LLM is explicitly unloaded (`keep_alive: 0`) before the render stage starts
- rendering is code-driven (Revideo/headless Chromium), not model inference — no GPU dependency, no VRAM budget to design around
- a fixed, hand-written library of scene generators is reused across every job; only the *data* driving them (which components, what text, what timing) is agent-generated — never code

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
              ├───► [ Video Path ]  ──► Revideo render (dispatched scenes) ──► FFmpeg encode
              │
              └───► [ Poster Path ] ──► Revideo poster render (single frame)
```

## Pipeline stages

1. **Agent swarm** (`Qwen2.5-1.5B` via Ollama) — strategy, script, quality inspection, then a composition-spec agent (video) or poster-layout agent (poster), run sequentially and unloaded from RAM before rendering starts.
2. **Poster path** — a `poster_layout_agent`-produced spec (headline, CTA text, two colors) rendered as a single still frame via `node render.mjs --project poster`.
3. **Video path** — a `composition_agent`-produced scene list (which fixed components, in what order, for how long) rendered via `node render.mjs --project video`, then muxed/encoded with FFmpeg.
4. **Platform adaptation** — reformats scripts and captions per target platform (TikTok, Instagram, X, LinkedIn).

See [docs-mpostele/00 Home](docs-mpostele/00%20Home.md) for the full design vault.

## A privacy and licensing note

Everything renders locally — no prompts or images leave the machine. Revideo (the render engine) is MIT-licensed across every package it depends on, so there's no licensing caveat on top of that, unlike the Remotion path this project used to run — see [docs-mpostele/07 Reference/02 Notes Archive](docs-mpostele/07%20Reference/02%20Notes%20Archive.md) for that history.

## Directory structure

```text
mpostele/
├── app/
│   ├── main.py              # CLI entry point
│   ├── cli.py               # shared --job arg parsing for every stage
│   ├── config/
│   │   └── settings.py      # Revideo/model/path config, all env-overridable
│   ├── orchestrator/
│   │   ├── state.py             # state.json read/append contract
│   │   ├── process_runner.py    # spawns each stage as its own subprocess
│   │   └── orchestrator.py      # the sequential control flow + quality gates
│   ├── agents/               # Ollama-backed swarm, one module per agent
│   │   ├── base.py              # call_ollama() + JSON extraction
│   │   ├── strategy_agent.py
│   │   ├── script_agent.py
│   │   ├── composition_agent.py       # video path only - scene list, not code
│   │   ├── composition_validator.py   # video path only - deterministic gate
│   │   ├── poster_layout_agent.py     # poster path only - headline/CTA/colors
│   │   ├── poster_validator.py        # poster path only - deterministic gate
│   │   ├── quality_inspector.py
│   │   └── platform_adaptor.py
│   └── media/
│       ├── memory.py            # unload_ollama_model
│       ├── revideo_cli.py       # shared node-binary resolution + subprocess wrapper
│       ├── poster_engine.py     # single-frame poster render
│       ├── video_engine.py      # dispatched-scene video render
│       ├── encode.py            # FFmpeg audio mux + final encode
│       ├── publish_engine.py    # opt-in: schedules the finished artifact via Postiz
│       └── assets/
│           ├── jobs/     # one state.json per job (gitignored)
│           ├── tmp/      # intermediate frames, purged on completion
│           ├── output/   # final posters/videos
│           └── fonts/    # unused now that rendering is Revideo-only
├── examples/
│   └── sample_brief.json
├── revideo/                # Node project - required, renders both paths
│   ├── render.mjs            # CLI entrypoint: node render.mjs --project video|poster --props <file> --out <path>
│   ├── schema.mjs            # plain-JS zod twin of src/schema.ts, used by render.mjs
│   └── src/
│       ├── video-project.ts    # data-driven master scene, the only place component names resolve to code
│       ├── poster-project.ts   # single-frame poster project
│       ├── schema.ts           # Zod schemas, mirror the two validator agents' shapes
│       └── scenes/             # fixed, hand-written generators (title-reveal, caption-overlay, outro, poster)
├── requirements.txt
├── README.md
├── LICENSE
└── docs-mpostele/
```

## Quickstart

```bash
pip install -r requirements.txt
ollama pull qwen2.5:1.5b && ollama serve &
cd revideo && npm install && cd ..
python -m app.main --media-type poster --brief-file examples/sample_brief.json
python -m app.main --media-type video --brief-file examples/sample_brief.json
```

Font files aren't needed (Revideo/CSS handles all text rendering) — see [docs-mpostele/05 Implementation/03 Setup Checklist](docs-mpostele/05%20Implementation/03%20Setup%20Checklist.md) for the full environment checklist.

Add `--publish` (or `--publish-now`) to also schedule the finished artifact to social platforms via a self-hosted or hosted [Postiz](https://docs.postiz.com/public-api) instance — opt-in, and off by default. See [docs-mpostele/03 Workflow/05 Platform Adaptation & Export](docs-mpostele/03%20Workflow/05%20Platform%20Adaptation%20%26%20Export.md) for setup and behavior.

## Project goals

- generate both short-form video and high-resolution poster output from the same agent swarm
- keep every generation stage transient, explicitly memory-unloaded (Ollama), and easy to reason about
- keep rendering code-driven and deterministic: a small, hand-written scene library, driven only by agent-generated data, never agent-generated code
- keep the stack free and open source, genuinely so — every dependency, Revideo included, is MIT/permissively licensed

## Summary

This repo is built around a sequential execution contract: an LLM agent swarm plans the content, then hands off to a Revideo-based poster or video renderer, with strict process isolation and an explicit Ollama-unload hook before rendering starts. It favors a small, reliable, fully-local rendering path over chasing higher-fidelity generative output.
