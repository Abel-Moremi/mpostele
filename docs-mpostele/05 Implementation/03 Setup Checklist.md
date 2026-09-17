# Setup Checklist

## Environment

- [ ] verify Python version and dependencies
- [ ] install Ollama and pull `qwen2.5:1.5b`
- [ ] install `torch` + `diffusers` (or equivalent) with CUDA support for the 1050 Ti
- [ ] download SD1.5 (and an LCM/Turbo variant) checkpoint weights
- [ ] install the AnimateDiff motion module
- [ ] install RIFE and FFmpeg, confirm codec/NVENC support
- [ ] configure remote dispatch credentials (Colab/Modal/RunPod) for Wan2.1

## Project files

- [ ] create the application structure (orchestrator, agents, media engines)
- [ ] define the `state.json` schema and job directory layout
- [ ] prepare configuration defaults (VRAM budget, retry limits, cleanup policy)

## Production flow

- [ ] run the agent swarm end to end for a sample strategy brief
- [ ] confirm `keep_alive: 0` releases the Ollama model before the diffusion stage starts
- [ ] render a sample poster and a sample video job
- [ ] confirm platform-adapted captions are produced for all four target platforms

## Validation

- [ ] measure actual VRAM usage during the poster pass and the AnimateDiff pass
- [ ] confirm no process holds CUDA context across a stage boundary
- [ ] verify intermediate artifacts are purged after job completion
- [ ] test remote dispatch failure/timeout handling and confirm the local fallback still works standalone

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
