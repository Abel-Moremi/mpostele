# Agent Pipeline Swarm

The agent swarm is the planning layer of the pipeline. It runs sequentially, one prompt at a time, on `Qwen2.5-1.5B` via Ollama, and is fully unloaded from RAM before any diffusion stage begins.

## Agents

1. **Strategy & Trend Agent** — turns business guidelines and campaign inputs into target hooks and calls to action.
2. **Script & Layout Agent** — generates spoken scripts, visual concepts, and text overlays.
3. **Keyframe Prompt Agent** — translates visual concepts into diffusion prompts, including negative-space constraints for posters.
4. **Motion Director Agent** — converts script hooks into camera movement prompts for video generation.
5. **Poster Composition Agent** — converts visual copy into a structured coordinate map (X, Y, W, H, typography, color hexes) plus maximum text boundary allocations.
6. **Quality Inspector Agent** — validates output against constraints such as text length limits and prompt style rules.
7. **Platform Adaptor Agent** — formats raw scripts into platform-native copy (TikTok, Instagram, X, LinkedIn).
8. **Execution Dispatcher** — routes tasks to local CPU/GPU engines or a remote runtime.

## Retry behavior

The Quality Inspector can send work back to the Script & Layout Agent when validation fails, capped at **2 retry cycles**. After that, the orchestrator falls back to default layout/prompt metrics and proceeds rather than looping indefinitely.

## Memory behavior

Every agent call is its own prompt against the already-running Ollama server — not a new model load per call. Before the pipeline branches into the poster or video path, the orchestrator issues `keep_alive: 0` to release `Qwen2.5-1.5B` from system RAM.

## State contract

Each agent reads the current `state.json` and appends its own structured block (`strategy_brief`, `content`, `keyframe_prompt`, `poster_layout`, …) rather than passing data in memory between stages.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/05 Ollama Agent Notes]]
