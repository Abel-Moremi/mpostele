# Memory & Process Protocol

This stage isn't a pipeline phase itself — it's the contract every phase transition follows to keep the pipeline reliable and debuggable.

## Process isolation

Every generation step (LLM call, Remotion render, FFmpeg encode) is spawned via `subprocess.run`, never imported into a single long-lived process. A subprocess dying at the end of its stage reclaims whatever memory it used regardless of any in-process cleanup.

## Explicit unload hook

```python
import requests

def unload_ollama_model(model_name: str = "qwen2.5:1.5b"):
    """Forces Ollama to release the resident LLM from system RAM."""
    try:
        requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model_name, "keep_alive": 0},
            timeout=5
        )
    except Exception as e:
        print(f"Warning: Failed to unload Ollama model: {e}")
```

`unload_ollama_model` runs before the pipeline branches into the poster or video render stage. There's no equivalent flush needed on the render side — Remotion's headless-Chromium subprocess holds no GPU context, so process exit alone reclaims everything it used.

## Standing daemon caveat

`ollama serve` itself is a long-running background process — unloading a model with `keep_alive: 0` releases that model's RAM footprint, but the Ollama server process stays up. Treat the Ollama server as infrastructure (like a database), not as one of the transient per-stage subprocesses.

## Resource constraints

- Quality/Composition/Poster validator retries capped at 2 cycles each
- intermediate render props and temp files purged on job completion — only final artifacts remain

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[06 Operations/03 Hardware Constraints]]
- [[06 Operations/02 Troubleshooting]]
