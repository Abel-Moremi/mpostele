# Architecture

## High-level pipeline

```text
Site Discovery Agent
    ↓
Evidence Graph & Content Planning
    ↓
Script, Voice & Screenshot Capture
    ↓
Animation Engine
    ↓
Compositing & Encoding
    ↓
Final Posting / Export
```


## Components

### 1. Site discovery and shared knowledge

`pipeline/site_agent` runs a bounded observe-plan-act-verify loop over one allowed website domain. Playwright gathers semantic DOM data, accessibility snapshots, screenshots, and controls. A deterministic policy blocks destructive, consequential, external, and unknown interactions before the reasoning provider can select an action.

Observed pages, UI states, controls, and verified transitions are stored in local SQLite. Agent interpretations are separate `findings` records with evidence references and confidence. `snapshot.json` is a versioned portable handoff contract for future content-planning, recording, and rendering agents; `decisions.jsonl` preserves reasoning and fallback events for debugging. The default semantic provider is a local OpenAI-compatible llama.cpp server, while a deterministic heuristic provider supports testing and model-free runs.

The first implementation crawls links and selected reversible controls sequentially. It intentionally does not submit forms, perform destructive actions, claim complete coverage, or automatically create videos. Authenticated discovery accepts a pre-created Playwright storage-state file rather than storing credentials.

### 2. Evidence-backed content planning

`pipeline.site_agent.content_plan` reads the portable discovery snapshot plus optional human review metadata. Deterministic preprocessing requires screenshot-backed states, removes rejected transitions, ranks important pages and flows, and bounds the candidate set. A heuristic provider works fully offline; an optional local llama.cpp provider can improve selection and wording and falls back to the heuristic provider on failure.

Provider output is not trusted directly. The planner rejects unknown or duplicate state IDs, enforces scene and narration-word budgets, and expands accepted proposals into versioned `content-plan.json` records with page, state, finding, transition, and screenshot references. Plans always start as `pending_review` and do not authorize capture, rendering, or publishing. A future frontend approval step will convert accepted scenes into a draft render-job manifest.


### 3. Screenshot capture


Playwright can record product screens, landing pages, or feature interactions. These frames become the base visual elements for the final video.

### 4. Animation engine


This is where motion is created using low-memory tools:

- static screenshots with FFmpeg pan/zoom
- CSS or JS animation in a browser
- Manim overlays for text and feature highlights

### 5. Voice & audio


`pipeline/tts.py` optionally uses local Kokoro synthesis to produce a cached WAV from a scene script. The dependency is lazy and separate from the base requirements, while `pipeline/audio.py` continues to accept any supplied narration recording.


### 6. Compositing and encoding


`pipeline/render_job.py` coordinates the existing modules from a local JSON manifest. It renders each URL, image, or video scene; applies optional overlays; uses either supplied narration or a generated script; then uses FFmpeg to normalize all scenes to matching H.264/AAC streams and concatenate them. The default `libx264` path is portable and does not require a GPU. Hardware encoding can remain an optional future optimization rather than an architectural dependency.


The orchestrator leaves captures, overlays, generated narration and its cache record, narrated clips, normalized scenes, and the concat list in a visible work directory. This makes reruns and failures understandable on modest hardware instead of hiding state in a service or opaque cache.


## Practical fit

This architecture matches the hardware constraints because it avoids heavy neural video generation models and relies on efficient rendering, compositing, and browser-driven motion.

## Related notes

- [[03 Workflow/01 Asset Capture]]
- [[03 Workflow/02 Animation Engine]]
- [[03 Workflow/03 Voice & Audio]]
- [[03 Workflow/04 Compositing]]
- [[03 Workflow/05 Final Export]]
