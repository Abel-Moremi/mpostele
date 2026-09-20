# Roadmap

## Phase 1: Foundation

- define the `state.json` data contract and job lifecycle
- build the orchestrator's subprocess spawn/kill loop
- verify Ollama runs locally

## Phase 2: Agent swarm

- implement the agents (strategy, script, quality inspector, composition director + composition validator, poster layout + poster validator, platform adaptor)
- wire each validator's bounded 2-retry loop
- confirm `keep_alive: 0` reliably releases `Qwen2.5-1.5B` before rendering starts

## Phase 3: Poster path

- `poster_layout_agent` producing a headline/CTA/color spec
- `remotion/src/scenes/Poster.tsx` + `npx remotion still` rendering it
- validate against the `poster_layout` schema end to end

## Phase 4: Video path

- `composition_agent` producing a scene-list spec
- `remotion/src/MainComposition.tsx` + `npx remotion render` rendering it
- FFmpeg audio mux/encode

## Phase 5: Memory & process protocol

- explicit Ollama unload hook before rendering starts
- cleanup of intermediate props/temp files on job completion
- confirm process isolation holds under repeated runs

## Phase 6: Platform adaptation & automation

- Platform Adaptor Agent output for TikTok/Instagram/X/LinkedIn
- CLI entry point for running jobs end to end
- package the workflow for reuse

## Superseded phases

An earlier version of this roadmap planned local SD1.5/AnimateDiff generation and remote Wan2.1 dispatch for the video path, and Pillow compositing for the poster path. That stack was built, confirmed working, and then removed in favor of Remotion once it proved more reliable in practice — see [[04 Research/01 Local Diffusion Model Options]].

## Related notes

- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]
