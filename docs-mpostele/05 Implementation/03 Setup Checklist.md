# Setup Checklist

## Environment

- [ ] verify Python version and dependencies (`pip install -r requirements.txt`)
- [ ] install Ollama and pull `qwen2.5:1.5b`
- [ ] install Node.js + npm, then `cd revideo && npm install` (required for both the poster and video paths)
- [ ] install FFmpeg (needed for the final video encode/mux pass)

## Project files

- [ ] create the application structure (orchestrator, agents, media engines)
- [ ] define the `state.json` schema and job directory layout
- [ ] prepare configuration defaults (retry limits, cleanup policy)

## Production flow

- [ ] run the agent swarm end to end for a sample strategy brief
- [ ] confirm `keep_alive: 0` releases the Ollama model before rendering starts
- [ ] render a sample poster (`python -m app.main --media-type poster --brief-file examples/sample_brief.json`) and a sample video (`--media-type video`)
- [ ] confirm platform-adapted captions are produced for all four target platforms

## Validation

- [ ] confirm no process outlives its stage (no orphaned Node/Chromium processes after a render)
- [ ] verify intermediate artifacts are purged after job completion
- [ ] `ffprobe` a rendered video's resolution/fps/duration against `app/config/settings.py`'s `REVIDEO_WIDTH/HEIGHT/FPS`

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
