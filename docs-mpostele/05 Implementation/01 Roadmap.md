 # Roadmap

## Current status

The repo now has a working local media pipeline and frontend from capture through optional local TTS and multi-scene export. It also has the first evidence-first site discovery agent foundation: bounded same-domain exploration, conservative action policy, local reasoning adapter, and reusable SQLite/JSON knowledge storage. Deeper form-based flows, content-plan generation, final voice pacing, and real-platform uploads remain future milestones.


## Phase 1: Foundation

- [x] define the project pipeline and goals
- [x] establish the design and research structure
- [x] prototype a browser-based planning interface
- [x] verify the local toolchain for automation work
- [x] validate the capture/FFmpeg/Manim strategy within the target memory budget

## Phase 2: Capture

- [x] set up Playwright browser automation
- [x] capture screenshots and landing page states
- [x] build a reliable visual asset pipeline (platform detection, verified login completion, hide/scope selectors, content-based duration estimate)

## Phase 3: Motion

- [x] add FFmpeg zoom and pan presets (`zoom_in`, `zoom_out`, 4x pan directions, `static`)
- [x] integrate Manim overlays for text and emphasis (`title`, `callout`, composited over the base clip with FFmpeg)
- [x] test browser-based motion sequences (`--capture-mode motion`: Playwright records a real hover/click/scroll interaction, transcoded to mp4 with FFmpeg)

## Phase 4: Audio

- [x] configure an optional Kokoro TTS workflow with deterministic WAV caching
- [x] align supplied local narration with scene timing (`pipeline/audio.py` probes duration, then trims or extends the visual)
- [x] add lightweight narration normalization and AAC encoding
- [ ] tune generated narration pacing and background clean-up

## Phase 5: Composite and export

- [x] merge a single motion/overlay clip with supplied voiceover
- [x] merge multiple clips, overlays, and voiceover into a complete sequence
- [x] add automated technical export checks for codec, dimensions, frame rate, audio, duration, and fast-start layout
- [ ] test validated output through real platform uploads
- [x] add landscape, vertical, and square export presets

## Phase 6: Automation

- [x] build a simple JSON-driven Python orchestrator (`pipeline/render_job.py`)
- [x] automate repeated rendering jobs while retaining inspectable intermediate files
- [x] add dependency-free wall-time and process-tree memory benchmarking
- [x] expose multi-scene jobs in the frontend through a loopback-only local endpoint
- [x] package an initial reusable local vertical render-job template
- [ ] package additional production render-job templates

## Phase 7: Site understanding agents

- [x] define a versioned shared knowledge schema for pages, states, actions, transitions, and findings
- [x] add a bounded Playwright discovery loop with deterministic URL and action safety checks
- [x] add local llama.cpp and deterministic heuristic reasoning providers
- [x] preserve screenshots, accessibility evidence, decision logs, SQLite state, and portable JSON snapshots
- [ ] add declarative authenticated and form-based workflow scenarios
- [ ] add deeper nested UI-state exploration and resume scheduling from the persisted frontier
- [ ] generate evidence-backed content plans for downstream recording agents
- [ ] expose discovery configuration and graph review in the frontend

## Related notes


- [[05 Implementation/02 Milestones]]
- [[05 Implementation/03 Setup Checklist]]
