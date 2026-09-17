"""Explicit memory-unload hooks between pipeline phases.

See docs-mpostele/03 Workflow/04 Memory & Process Protocol.md: flush_cuda_memory
is meant to run inside the dying diffusion subprocess itself, right before it
exits - the orchestrator process never holds a CUDA context to flush.
"""
import gc

import requests

from app.config import settings


def unload_ollama_model(model_name: str = None) -> None:
    """Forces Ollama to release the resident LLM from system RAM."""
    try:
        requests.post(
            f"{settings.OLLAMA_HOST}/api/generate",
            json={"model": model_name or settings.OLLAMA_MODEL, "keep_alive": 0},
            timeout=5,
        )
    except requests.RequestException as exc:
        print(f"Warning: failed to unload Ollama model: {exc}")


def flush_cuda_memory() -> None:
    """Clears the PyTorch CUDA cache and runs garbage collection."""
    gc.collect()
    try:
        import torch
    except ImportError:
        return
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
