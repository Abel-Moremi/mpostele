"""Explicit memory-unload hook between the LLM planning phase and rendering.

See docs-mpostele/03 Workflow/04 Memory & Process Protocol.md.
"""
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
