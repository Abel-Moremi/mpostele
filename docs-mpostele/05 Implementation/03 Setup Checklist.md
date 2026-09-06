# Setup Checklist

## Current status

The repository currently includes:

- [x] project documentation and architecture notes
- [x] a Vite + Vue frontend prototype
- [x] shared design tokens and styling foundation
- [x] JSON-driven multi-scene pipeline and frontend editor

The remaining environment and production validation work is still pending:


## Environment

- [ ] verify Python version and dependencies for the pipeline
- [ ] install Playwright and browser runtime
- [ ] install FFmpeg and confirm codec support
- [x] install Manim for overlay rendering (`pip install -r requirements.txt`, CPU-only)
- [x] define optional Kokoro installation (`pip install -r requirements-tts.txt`)
- [ ] populate and verify the Kokoro model/voice cache on the production machine

- [ ] verify PCIe and GPU acceleration support for NVENC

## Project files

- [x] create the application structure for automation scripts
- [x] plan visible work and output directories through render manifests
- [x] prepare configuration defaults and export presets
- [x] add a production-oriented multi-scene CLI entry point

## Production flow

- [x] capture screenshots reliably
- [x] render animation overlays
- [x] compose a supplied local voiceover with one motion layer
- [x] generate and cache voiceover locally from a script

- [x] orchestrate multi-scene short-form video output from the CLI and frontend

## Validation

- [x] test first short video render
- [ ] verify memory usage stays within target limits
- [ ] check output quality and playback stability

The local pipeline now combines Playwright capture, FFmpeg motion, Manim overlays, supplied or optional Kokoro-generated narration, and normalized multi-scene export. The frontend Render panel creates, validates, persists, and executes render jobs through a loopback-only endpoint. FFmpeg and FFprobe must both be available on `PATH`. Kokoro remains an optional install and its assets must be cached before offline use; hardware and production-platform validation remain pending.


## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
