from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib.request import Request, urlopen

from .models import Analysis, Observation


class ReasoningProvider(Protocol):
    name: str

    def analyze(self, observation: Observation, safe_action_ids: list[str]) -> Analysis: ...


@dataclass
class HeuristicProvider:
    """Offline deterministic fallback used for testing and model-free runs."""

    name: str = "heuristic"

    def analyze(self, observation: Observation, safe_action_ids: list[str]) -> Analysis:
        purpose = observation.headings[0] if observation.headings else observation.title
        summary = f"Page titled {observation.title!r} with {len(observation.controls)} visible controls."
        return Analysis(summary=summary, purpose=purpose, selected_action_ids=safe_action_ids[:3])


@dataclass
class LlamaCppProvider:
    endpoint: str = "http://127.0.0.1:8080/v1/chat/completions"
    model: str = "qwen3-4b-instruct"
    timeout_seconds: float = 120.0
    name: str = "llama.cpp"

    def analyze(self, observation: Observation, safe_action_ids: list[str]) -> Analysis:
        controls = [
            {"id": item.id, "role": item.role, "name": item.name, "href": item.href}
            for item in observation.controls
        ]
        prompt = {
            "url": observation.url,
            "title": observation.title,
            "headings": observation.headings,
            "visible_text": observation.visible_text[:6000],
            "controls": controls,
            "safe_action_ids": safe_action_ids,
        }
        body = {
            "model": self.model,
            "temperature": 0.1,
            "max_tokens": 700,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You analyze product websites using only supplied evidence. Return JSON with "
                        "summary, purpose, selected_action_ids, and findings. findings is a list of "
                        "objects with kind, statement, confidence. Never select an ID outside "
                        "safe_action_ids and never invent product claims. Prefer actions that reveal "
                        "new product capabilities."
                    ),
                },
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request, timeout=self.timeout_seconds) as response:
            result = json.loads(response.read().decode("utf-8"))
        content = result["choices"][0]["message"]["content"]
        parsed = json.loads(content)
        selected = [item for item in parsed.get("selected_action_ids", []) if item in safe_action_ids]
        findings = []
        for item in parsed.get("findings", []):
            if not isinstance(item, dict) or not str(item.get("statement", "")).strip():
                continue
            findings.append(
                {
                    "kind": str(item.get("kind", "page_interpretation")),
                    "statement": str(item["statement"]).strip(),
                    "confidence": float(item.get("confidence", 0.5)),
                }
            )
        return Analysis(
            summary=str(parsed.get("summary", "")).strip(),
            purpose=str(parsed.get("purpose", observation.title)).strip(),
            selected_action_ids=selected,
            findings=findings,
        )
