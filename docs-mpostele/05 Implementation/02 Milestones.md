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

## Superseded milestones

Earlier milestones covered local SD1.5/AnimateDiff generation, a remote Wan2.1 dispatch client, RIFE interpolation, and a Pillow compositor — all built, measured, and later removed in favor of the Remotion-only pipeline above. See [[04 Research/01 Local Diffusion Model Options]].

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/03 Setup Checklist]]
