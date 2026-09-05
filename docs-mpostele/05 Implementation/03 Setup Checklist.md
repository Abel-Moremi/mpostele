# Setup Checklist

## Current status

The repository currently includes:

- [x] project documentation and architecture notes
- [x] a Vite + Vue frontend prototype
- [x] shared design tokens and styling foundation

The remaining production pipeline work is still pending:

## Environment

- [ ] verify Python version and dependencies for the pipeline
- [ ] install Playwright and browser runtime
- [ ] install FFmpeg and confirm codec support
- [x] install Manim for overlay rendering (`pip install -r requirements.txt`, CPU-only)
- [ ] install TTS tooling such as Kokoro
- [ ] verify PCIe and GPU acceleration support for NVENC

## Project files

- [ ] create the application structure for automation scripts
- [ ] plan the media asset directories
- [ ] prepare configuration defaults
- [ ] add the first production-oriented CLI entry point

## Production flow

- [ ] capture screenshots reliably
- [ ] render animation overlays
- [ ] compose voiceover with motion layers
- [ ] export short-form video output

## Validation

- [x] test first short video render
- [ ] verify memory usage stays within target limits
- [ ] check output quality and playback stability

The first render proof is now in place with a local Playwright capture and FFmpeg zoom-pan export flow. This establishes the minimum viable architecture before adding richer motion overlays and audio.

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/02 Milestones]]
