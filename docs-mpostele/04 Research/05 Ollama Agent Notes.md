# Ollama Agent Notes

Notes on running the agent swarm against a locally-served `Qwen2.5-1.5B` model.

## Model choice

`Qwen2.5-1.5B` is small enough to load quickly and cheaply on 8GB system RAM, while still being capable enough for the swarm's structured, task-specific prompts (strategy, script, keyframe prompt, layout, QA, platform adaptation).

## Unload pattern

Ollama's server process (`ollama serve`) stays running as infrastructure. Individual models are released from RAM by calling `/api/generate` with `keep_alive: 0`:

```python
requests.post(
    "http://localhost:11434/api/generate",
    json={"model": "qwen2.5:1.5b", "keep_alive": 0},
    timeout=5
)
```

This must run before any diffusion subprocess is spawned — it releases RAM, not VRAM, but on an 8GB machine that headroom still matters once SD1.5/AnimateDiff processes start allocating their own working memory.

## Invocation pattern

Each agent call is a single prompt sent to the already-running server, executed from its own short-lived subprocess on the orchestrator side — the LLM call itself doesn't need process-per-call isolation the way diffusion does, since Ollama already manages the model's residency; the subprocess boundary here is about keeping the orchestrator's own code decoupled from any one stage's failure.

## Related notes

- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[03 Workflow/04 Memory & Process Protocol]]
- [[04 Research/02 Tool Comparison]]
