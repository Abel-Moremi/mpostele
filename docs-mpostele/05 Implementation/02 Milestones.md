# Milestones

## Milestone 1: repo and docs foundation

- initialize the project structure
- document the sequential execution contract and hardware constraints
- define the `state.json` schema

## Milestone 2: agent swarm

- get Ollama serving `Qwen2.5-1.5B` locally
- implement all 8 agents against the state contract
- validate the quality-inspector retry loop end to end

## Milestone 3: poster path

- SD1.5 background generation under budget
- Pillow compositor producing a final poster from a sample `poster_layout`
- fix the known word-wrap edge cases (see [[04 Research/04 Pillow Compositor Notes]])

## Milestone 4: video path

- measure AnimateDiff's real VRAM footprint on the 1050 Ti at various frame counts
- stand up the Wan2.1 remote dispatch client
- RIFE + FFmpeg producing a final encoded clip

## Milestone 5: full pipeline

- run a job end to end for both media types
- confirm memory unload hooks and process isolation hold under repeated runs
- confirm intermediate artifact cleanup actually fires on completion

## Related notes

- [[05 Implementation/01 Roadmap]]
- [[05 Implementation/03 Setup Checklist]]
