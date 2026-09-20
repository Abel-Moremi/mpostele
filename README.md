# mpostele

mpostele is a local-first, autonomous content studio for generating **short-form marketing videos** and **high-resolution static posters**, driven by an LLM planning swarm and rendered entirely through code — no diffusion model, no GPU, no VRAM budget to manage.

The project originally ran local diffusion models (SD1.5, AnimateDiff) under a hard 4GB VRAM / 8GB RAM budget, with a remote Wan2.1 dispatch path for higher fidelity. That whole stack was removed in favor of a single, simpler approach: Remotion (a Node/React framework that renders video via headless Chromium) renders both the video and poster paths from data the agent swarm produces. It's the only path that was ever confirmed reliable without a driver-, VRAM-, or network-dependency to manage — see [docs-mpostele/04 Research/01 Local Diffusion Model Options](docs-mpostele/04%20Research/01%20Local%20Diffusion%20Model%20Options.md) for why the diffusion path was dropped.

## Why this project exists

Continuous background microservices and resident LLM instances still aren't free — the design keeps every generation step disposable rather than resident:

- every pipeline stage executes as a **transient, single-responsibility subprocess**
- the Ollama LLM is explicitly unloaded (`keep_alive: 0`) before the render stage starts
- rendering is code-driven (Remotion/headless Chromium), not model inference — no GPU dependency, no VRAM budget to design around
- a fixed, hand-written library of scene/poster components is reused across every job; only the *data* driving them (which components, what text, what timing) is agent-generated — never code

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
              ├───► [ Video Path ]  ──► Remotion render (Series of scenes) ──► FFmpeg encode
              │
              └───► [ Poster Path ] ──► Remotion still render (single frame)
```

## Pipeline stages

1. **Agent swarm** (`Qwen2.5-1.5B` via Ollama) — strategy, script, quality inspection, then a composition-spec agent (video) or poster-layout agent (poster), run sequentially and unloaded from RAM before rendering starts.
2. **Poster path** — a `poster_layout_agent`-produced spec (headline, CTA text, two colors) rendered as a single still frame via `npx remotion still`.
3. **Video path** — a `composition_agent`-produced scene list (which fixed components, in what order, for how long) rendered via `npx remotion render`, then muxed/encoded with FFmpeg.
4. **Platform adaptation** — reformats scripts and captions per target platform (TikTok, Instagram, X, LinkedIn).

See [docs-mpostele/00 Home](docs-mpostele/00%20Home.md) for the full design vault.

## A privacy and licensing note

Everything renders locally — no prompts or images leave the machine. The one thing to check before relying on this beyond personal/small-scale use: Remotion's license requires a paid company license past a small-team size (see remotion.dev/license), which is worth weighing against this project's goal of staying free and open source.

## Directory structure

```text
mpostele/
├── app/
│   ├── main.py              # CLI entry point
│   ├── cli.py               # shared --job arg parsing for every stage
│   ├── config/
│   │   └── settings.py      # Remotion/model/path config, all env-overridable
│   ├── orchestrator/
│   │   ├── state.py             # state.json read/append contract
│   │   ├── process_runner.py    # spawns each stage as its own subprocess
│   │   └── orchestrator.py      # the sequential control flow + quality gates
│   ├── agents/               # Ollama-backed swarm, one module per agent
│   │   ├── base.py              # call_ollama() + JSON extraction
│   │   ├── strategy_agent.py
│   │   ├── script_agent.py
│   │   ├── composition_agent.py       # video path only - scene list, not JSX
│   │   ├── composition_validator.py   # video path only - deterministic gate
│   │   ├── poster_layout_agent.py     # poster path only - headline/CTA/colors
│   │   ├── poster_validator.py        # poster path only - deterministic gate
│   │   ├── quality_inspector.py
│   │   └── platform_adaptor.py
│   └── media/
│       ├── memory.py            # unload_ollama_model
│       ├── poster_engine.py     # `remotion still` - single-frame poster render
│       ├── video_engine.py      # `remotion render` - Series-based video render
│       ├── encode.py            # FFmpeg audio mux + final encode
│       └── assets/
│           ├── jobs/     # one state.json per job (gitignored)
│           ├── tmp/      # intermediate frames, purged on completion
│           ├── output/   # final posters/videos
│           └── fonts/    # unused now that rendering is Remotion-only
├── examples/
│   └── sample_brief.json
├── remotion/              # Node/React project - required, renders both paths
│   └── src/
│       ├── index.ts
│       ├── Root.tsx           # registers MainComposition (video) + Poster (still)
│       ├── schema.ts          # Zod schemas, mirror the two validator agents' shapes
│       ├── MainComposition.tsx  # data-driven <Series>, the only place component names resolve to code
│       └── scenes/            # fixed, hand-written components (TitleReveal, CaptionOverlay, Outro, Poster)
├── requirements.txt
├── README.md
├── LICENSE
└── docs-mpostele/
```

## Quickstart

```bash
pip install -r requirements.txt
ollama pull qwen2.5:1.5b && ollama serve &
cd remotion && npm install && cd ..
python -m app.main --media-type poster --brief-file examples/sample_brief.json
python -m app.main --media-type video --brief-file examples/sample_brief.json
```

Font files aren't needed (Remotion/CSS handles all text rendering) — see [docs-mpostele/05 Implementation/03 Setup Checklist](docs-mpostele/05%20Implementation/03%20Setup%20Checklist.md) for the full environment checklist.

## Project goals

- generate both short-form video and high-resolution poster output from the same agent swarm
- keep every generation stage transient, explicitly memory-unloaded (Ollama), and easy to reason about
- keep rendering code-driven and deterministic: a small, hand-written component library, driven only by agent-generated data, never agent-generated code
- keep the stack free and open source (see the licensing note above for the one open risk to that goal)

## Summary

This repo is built around a sequential execution contract: an LLM agent swarm plans the content, then hands off to a Remotion-based poster or video renderer, with strict process isolation and an explicit Ollama-unload hook before rendering starts. It favors a small, reliable, fully-local rendering path over chasing higher-fidelity generative output.
