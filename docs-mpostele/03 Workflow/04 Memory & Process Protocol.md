# Memory & Process Protocol

This stage isn't a pipeline phase itself — it's the contract every phase transition must follow to stay within the 4GB VRAM / 8GB RAM budget.

## Process isolation

Every generation step is spawned via `subprocess.run`, never imported into a single long-lived process. A subprocess dying at the end of its stage reclaims its VRAM/RAM regardless of whether an in-process flush ran — the explicit hooks below are a second, faster layer on top of that guarantee, not a replacement for it.

## Explicit unload hooks

```python
import gc
import requests
import torch

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

def flush_cuda_memory():
    """Clears PyTorch CUDA memory cache and triggers Python garbage collection."""
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
```

`unload_ollama_model` runs before the pipeline branches into the poster or video path. `flush_cuda_memory` should run **inside the diffusion child process itself, right before it exits** — the orchestrator process never holds a CUDA context, so it has nothing to flush; it only decides when to kill the child and start the next one.

## Standing daemon caveat

`ollama serve` itself is a long-running background process — unloading a model with `keep_alive: 0` releases that model's RAM/VRAM footprint, but the Ollama server process stays up. Treat the Ollama server as infrastructure (like a database), not as one of the transient per-stage subprocesses.

## Resource constraints

- diffusion capped at SD1.5-class models, fp16, with VRAM-reduction settings appropriate to the actual inference library in use
- temporary diffusion frames and state written to fast local temp storage; a RAM-backed disk trades I/O speed for RAM headroom and should be sized carefully against the 8GB budget rather than assumed free
- Quality Inspector retries capped at 2 cycles
- intermediate frames, raw diffusion dumps, and temp audio purged on job completion — only final artifacts remain

## Related notes

- [[02 Architecture]]
- [[03 Workflow/01 Agent Pipeline Swarm]]
- [[06 Operations/03 Hardware Constraints]]
- [[06 Operations/02 Troubleshooting]]
