# Roadmap

## Current status

The repo has completed the documentation foundation and a frontend prototype. The actual media-generation pipeline remains the next major implementation milestone.

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
- [ ] integrate Manim overlays for text and emphasis
- [ ] test browser-based motion sequences

## Phase 4: Audio

- [ ] configure Kokoro TTS workflow
- [ ] align audio with the scene timing
- [ ] tune narration pacing and background clean-up

## Phase 5: Composite and export

- [ ] merge clips, overlays, and voiceover
- [ ] test final output for platform compatibility
- [ ] finalize export presets for social videos

## Phase 6: Automation

- [ ] build a simple CLI or Python orchestrator
- [ ] automate repeated rendering jobs
- [ ] package the workflow for reuse

## Related notes

- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]
