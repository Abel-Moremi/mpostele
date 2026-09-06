# Setup Checklist

## Current status

The repository currently includes:

- [x] project documentation and architecture notes
- [x] a Vite + Vue frontend prototype
- [x] shared design tokens and styling foundation
- [x] JSON-driven multi-scene pipeline and frontend editor

The remaining environment and production validation work is still pending:

## Environment

- [x] verify Python and base pipeline dependencies on the reference machine
- [x] install and exercise Playwright and its browser runtime
- [x] install FFmpeg/FFprobe and confirm H.264/AAC support
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
- [x] add automated codec, stream, dimensions, frame-rate, duration, and fast-start checks
- [x] add a repeatable local vertical demo manifest
- [x] run the vertical demo with representative supplied narration fixtures
- [x] verify process-tree memory usage stays within target limits on the reference laptop
- [ ] review pacing with final production voice recordings
- [ ] check output quality and playback stability on real platform uploads

The local pipeline now combines Playwright capture, FFmpeg motion, Manim overlays, supplied or optional Kokoro-generated narration, normalized multi-scene export, lightweight FFprobe-based output validation, and standard-library process-tree benchmarking. A narrated reference render on the target i5-7300HQ/8 GB/GTX 1050 Ti machine completed in 46.518 seconds with a 661.96 MiB peak render-process working set. FFmpeg and FFprobe must both be available on `PATH`. Kokoro remains optional and was not part of this supplied-WAV test; final voice pacing and production-platform uploads remain pending. See [[06 Operations/04 Production Validation]].

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
