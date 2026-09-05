# Milestones

## Milestone 1: repo and docs foundation

- [x] initialize the project structure
- [x] create the vault and core notes
- [x] document the architecture and design constraints

## Milestone 2: frontend prototype

- [x] create a browser-based planning dashboard
- [x] define the shared token and theme system
- [x] establish the visual storytelling foundation for product marketing UI

## Milestone 3: screenshot workflow

- [x] create a Playwright capture flow
- [x] collect and organize product visual assets
- [x] build a screenshot-to-scene abstraction
- [x] harden capture with platform detection, verified login completion, hide/scope selectors, and content-based duration estimation

The first local proof uses Playwright to capture a page and FFmpeg to export a short motion clip from that screenshot. The capture step now inspects the page before acting (is a login form actually present?), confirms a login actually completed instead of assuming a click worked, lets a job hide noisy elements or scope the shot to one element, and estimates clip duration from the amount of text in the captured scene rather than a fixed guess.

## Milestone 4: animation workflow

- [ ] add low-memory animation presets
- [ ] test FFmpeg motion effects
- [ ] add Manim overlays for callouts and titles

## Milestone 5: voiceover workflow

- [ ] generate script-based narration
- [ ] tune voice pacing and timing
- [ ] integrate audio into video layers

## Milestone 6: final pipeline

- [ ] assemble full video sequences
- [ ] generate final exports
- [ ] confirm the workflow works end to end

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/03 Setup Checklist]]
