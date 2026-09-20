# Milestones

## Milestone 1: repo and docs foundation

- initialize the project structure
- document the Sequential Execution Contract
- define the `state.json` schema

## Milestone 2: agent swarm

- get Ollama serving `Qwen2.5-1.5B` locally
- implement the agents against the state contract
- validate each validator's retry loop end to end

## Milestone 3: poster path

- `poster_layout_agent` producing a headline/CTA/color spec
- `npx remotion still` rendering `remotion/src/scenes/Poster.tsx` into a final poster PNG
- confirmed working end to end against a live Ollama server (2026-09-19)

## Milestone 4: video path

- `composition_agent` producing a scene-list spec
- `npx remotion render` rendering `remotion/src/MainComposition.tsx`'s `<Series>`, then FFmpeg encode
- confirmed working end to end against a live Ollama server (2026-09-19), including two real bugs found and fixed (Windows `npx` resolution, nvenc driver mismatch) — see [[06 Operations/02 Troubleshooting]]

## Milestone 5: full pipeline

- run a job end to end for both media types
- confirm the Ollama unload hook and process isolation hold under repeated runs
- confirm intermediate artifact cleanup actually fires on completion

## Milestone 6: Remotion → Revideo migration

- ported the four scene components (`TitleReveal`, `CaptionOverlay`, `Outro`, `Poster`) from Remotion (React/`useCurrentFrame`) to Revideo (generators/`tween`) 1:1, one deliberate behavior change (`CaptionOverlay`'s word-fade became a progressive `.text()` reveal - no Revideo equivalent for independently-animated inline text spans)
- replaced `npx remotion render/still` with a hand-written `revideo/render.mjs` CLI; no Revideo equivalent for Remotion's single-frame `still` mode, so the poster path renders a near-zero-duration clip and extracts frame 0 via `ffmpeg -frames:v 1`
- confirmed working end to end against a live Ollama server (2026-09-20), both media types, including the SVG decoration pipeline rendering into the final frame - see [[03 Workflow/03 Video Rendering Path]] and [[07 Reference/02 Notes Archive]] for the two real render-pipeline bugs found and fixed along the way

## Superseded milestones

Earlier milestones covered local SD1.5/AnimateDiff generation, a remote Wan2.1 dispatch client, RIFE interpolation, and a Pillow compositor — all built, measured, and later removed in favor of the Remotion-only pipeline above (itself later replaced by Revideo, milestone 6). See [[04 Research/01 Local Diffusion Model Options]].

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/03 Setup Checklist]]
