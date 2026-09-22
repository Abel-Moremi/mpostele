# Agent Pipeline Swarm

The agent swarm is the planning layer of the pipeline. It runs sequentially, one prompt at a time, mostly on `Qwen2.5-1.5B` via Ollama - one call (mood tagging) uses a second, larger `Qwen2.5-3B` "creative tier" instead, see [[04 Research/05 Ollama Agent Notes]] for why. Both models are fully unloaded from RAM before the Revideo render stage begins.

## Agents

1. **Strategy & Trend Agent** — turns business guidelines and campaign inputs into target hooks and calls to action. Video jobs also get a second, separate call on the creative-tier model tagging campaign mood (`calm`/`upbeat`/`corporate`) into `strategy_brief.mood`, consumed by `audio_engine.py`'s music pick - best-effort: a failed/unavailable creative model just omits the tag rather than failing the job, since this is the pipeline's first stage and isn't behind a retry gate.
2. **Script & Layout Agent** — generates spoken scripts, visual concepts, and text overlays.
3. **Quality Inspector Agent** — validates output against constraints such as text length limits.
4. **Creative Critic Agent** (both media types) — a holistic judgment call on the creative-tier model: does the hook/script body/call-to-action read naturally and cohere as one message, not just fit the length limits Quality Inspector already checked. Best-effort like the mood tag - a failed/unavailable creative model is treated as a pass, not a failure, since this is a quality bar on top of Quality Inspector's structural gate, not a new correctness dependency.
5. **Narration Engine** (video only, not an LLM agent) — splits the script into sentence-level segments, synthesizes each with Piper, and measures each one's real duration *before* composition runs, so scene timing can be derived from it rather than guessed.
6. **Composition Director Agent** (video only) — converts the script into a Revideo scene list: which fixed component, in what order, with what text/colors/transitions. One `CaptionOverlay` scene per narration segment, each duration assigned deterministically from that segment's real length (or a fixed title/outro beat), not decided by the LLM - its only remaining text job is adapting the hook/CTA into `TitleReveal`/`Outro` text. Which transition (crossfade/slide/matchCut) plays at each cut is proposed by the creative-tier model based on that cut's on-screen text, but Python is the safety net - it guarantees a valid, non-repeating result regardless of what (if anything) the model proposed, which is why this doesn't need its own validator/retry gate.
7. **Composition Validator Agent** (video only) — deterministic gate on the scene list before a render is spawned.
8. **Poster Composition Agent** (poster only) — converts visual copy into a headline, a short CTA label, and two colors. Revideo handles layout itself, so no coordinates or canvas math are needed here any more.
9. **Poster Validator Agent** (poster only) — deterministic gate on the poster spec before a render is spawned.
10. **Platform Adaptor Agent** — formats raw scripts into platform-native copy (TikTok, Instagram, X, LinkedIn).

## Retry behavior

Each gate (Quality Inspector, Creative Critic, Composition Validator, Poster Validator) can send work back to its upstream agent when validation fails, capped at **2 retry cycles**. After that, the orchestrator falls through and renders anyway rather than looping indefinitely. Gates are independent and don't cross-validate each other's concerns - a Creative Critic retry that changes the script isn't re-checked against Quality Inspector's length limits, same shape every other gate pair already has.

## Memory behavior

Every agent call is its own prompt against the already-running Ollama server — not a new model load per call. Before the pipeline branches into the poster or video path, the orchestrator issues `keep_alive: 0` twice, once per model, to release both `Qwen2.5-1.5B` and `Qwen2.5-3B` from system RAM.

## State contract

Each agent reads the current `state.json` and appends its own structured block (`strategy_brief`, `content`, `composition_spec`, `poster_layout`, …) rather than passing data in memory between stages.

## Related notes

- [[02 Architecture]]
- [[03 Workflow/02 Poster Rendering Path]]
- [[03 Workflow/03 Video Rendering Path]]
- [[04 Research/05 Ollama Agent Notes]]
