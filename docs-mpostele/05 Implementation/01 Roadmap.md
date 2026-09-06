 # Roadmap

## Current status

The repo now has a working local media pipeline and frontend from capture through multi-scene export. Local TTS and real-world platform validation remain the next major milestones.

## Phase 1: Foundation

- [x] define the project pipeline and goals
- [x] establish the design and research structure
- [x] prototype a browser-based planning interface
- [ ] verify the local toolchain for automation work
- [ ] decide the final hardware-safe animation strategy for production

## Phase 2: Capture

- [x] set up Playwright browser automation
- [x] capture screenshots and landing page states
- [x] build a reliable visual asset pipeline (platform detection, verified login completion, hide/scope selectors, content-based duration estimate)

## Phase 3: Motion

- [x] add FFmpeg zoom and pan presets (`zoom_in`, `zoom_out`, 4x pan directions, `static`)
- [x] integrate Manim overlays for text and emphasis (`title`, `callout`, composited over the base clip with FFmpeg)
- [x] test browser-based motion sequences (`--capture-mode motion`: Playwright records a real hover/click/scroll interaction, transcoded to mp4 with FFmpeg)

## Phase 4: Audio

- [ ] configure Kokoro TTS workflow
- [x] align supplied local narration with scene timing (`pipeline/audio.py` probes duration, then trims or extends the visual)
- [x] add lightweight narration normalization and AAC encoding
- [ ] tune generated narration pacing and background clean-up

## Phase 5: Composite and export

- [x] merge a single motion/overlay clip with supplied voiceover
- [x] merge multiple clips, overlays, and voiceover into a complete sequence
- [ ] test final output for platform compatibility
- [x] add landscape, vertical, and square export presets

## Phase 6: Automation

- [x] build a simple JSON-driven Python orchestrator (`pipeline/render_job.py`)
- [x] automate repeated rendering jobs while retaining inspectable intermediate files
- [x] expose multi-scene jobs in the frontend through a loopback-only local endpoint
- [ ] package reusable render-job templates

## Related notes

- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]
