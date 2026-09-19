# Setup Checklist

## Environment

- [ ] verify Python version and dependencies
- [ ] install Ollama and pull `qwen2.5:1.5b`
- [ ] install `torch` + `diffusers` (or equivalent) with CUDA support for the 1050 Ti
- [ ] download SD1.5 (and an LCM/Turbo variant) checkpoint weights
- [ ] install the AnimateDiff motion module
- [ ] install RIFE and FFmpeg, confirm codec/NVENC support
- [ ] get an ngrok authtoken (https://dashboard.ngrok.com/get-started/your-authtoken) and pick a shared-secret API key
- [ ] open [colab/wan21_server.ipynb](../../colab/wan21_server.ipynb) in Colab, fill in `NGROK_AUTH_TOKEN` and `API_KEY`, run every cell
- [ ] set `WAN21_REMOTE_ENDPOINT` (the printed ngrok URL) and `WAN21_API_KEY` (matching the notebook) on the local machine
- [ ] (optional, for `--execution-mode remotion`) install Node.js + npm, then `cd remotion && npm install`; check Remotion's license terms (remotion.dev/license) against your intended usage first

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
