"""Shared helpers for the Ollama-backed agent swarm."""
import json

import requests

from app.config import settings


def call_ollama(prompt: str, model: str = None) -> str:
    response = requests.post(
        f"{settings.OLLAMA_HOST}/api/generate",
        json={"model": model or settings.OLLAMA_MODEL, "prompt": prompt, "stream": False},
        timeout=settings.OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["response"]


def extract_json(text: str) -> dict:
    """Qwen2.5-1.5B doesn't always follow "JSON only" instructions exactly -
    pull out the first {...} block rather than assuming the whole response parses."""
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError(f"No JSON object found in model output: {text!r}")
    return json.loads(text[start : end + 1])
