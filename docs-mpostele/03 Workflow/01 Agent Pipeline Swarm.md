# Agent Pipeline Swarm

The agent swarm is the planning layer of the pipeline. It runs sequentially, one prompt at a time, on `Qwen2.5-1.5B` via Ollama, and is fully unloaded from RAM before the Remotion render stage begins.

## Agents

1. **Strategy & Trend Agent** — turns business guidelines and campaign inputs into target hooks and calls to action.
2. **Script & Layout Agent** — generates spoken scripts, visual concepts, and text overlays.
3. **Quality Inspector Agent** — validates output against constraints such as text length limits.
4. **Composition Director Agent** (video only) — converts the script into a Remotion scene list: which fixed component, in what order, for how long, with what text/colors. Data only, never JSX.
5. **Composition Validator Agent** (video only) — deterministic gate on the scene list before a render is spawned.
6. **Poster Composition Agent** (poster only) — converts visual copy into a headline, a short CTA label, and two colors. Remotion/CSS handles layout itself, so no coordinates or canvas math are needed here any more.
7. **Poster Validator Agent** (poster only) — deterministic gate on the poster spec before a render is spawned.
8. **Platform Adaptor Agent** — formats raw scripts into platform-native copy (TikTok, Instagram, X, LinkedIn).

## Retry behavior

Each gate (Quality Inspector, Composition Validator, Poster Validator) can send work back to its upstream agent when validation fails, capped at **2 retry cycles**. After that, the orchestrator falls through and renders anyway rather than looping indefinitely.

## Memory behavior

Every agent call is its own prompt against the already-running Ollama server — not a new model load per call. Before the pipeline branches into the poster or video path, the orchestrator issues `keep_alive: 0` to release `Qwen2.5-1.5B` from system RAM.

## State contract

Each agent reads the current `state.json` and appends its own structured block (`strategy_brief`, `content`, `composition_spec`, `poster_layout`, …) rather than passing data in memory between stages.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/05 Ollama Agent Notes]]
