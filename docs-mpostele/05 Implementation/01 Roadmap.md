# Roadmap

## Phase 1: Foundation

- define the `state.json` data contract and job lifecycle
- build the orchestrator's subprocess spawn/kill loop
- verify Ollama and a local SD1.5 checkpoint run on the target hardware

## Phase 2: Agent swarm

- implement the 8 agents (strategy, script, keyframe prompt, motion director, poster composition, quality inspector, platform adaptor, execution dispatcher)
- wire the Quality Inspector's bounded 2-retry loop
- confirm `keep_alive: 0` reliably releases `Qwen2.5-1.5B` before the next phase

## Phase 3: Poster path

- SD1.5 text-free background generation under the VRAM budget
- Pillow compositor: text wrapping, badges, logos
- validate against `poster_layout` schema end to end

## Phase 4: Video path

- local SD1.5 + AnimateDiff fallback, measure actual VRAM ceiling and frame-count limits on the 1050 Ti
- remote Wan2.1 dispatch client (Colab/Modal/RunPod)
- RIFE interpolation and FFmpeg audio mux/encode

## Phase 5: Memory & process protocol

- explicit unload hooks between every phase boundary
- cleanup of intermediate frames/dumps/temp audio on job completion
- confirm process isolation actually prevents cross-stage VRAM accumulation under load

## Phase 6: Platform adaptation & automation

- Platform Adaptor Agent output for TikTok/Instagram/X/LinkedIn
- CLI or simple orchestrator entry point for running jobs end to end
- package the workflow for reuse

## Related notes

- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]
