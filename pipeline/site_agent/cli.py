from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from .agent import AgentConfig, SiteDiscoveryAgent
from .reasoning import HeuristicProvider, LlamaCppProvider


def load_config(path: Path | str) -> AgentConfig:
    payload: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))
    allowed = payload.get("allowed_domains", ())
    payload["allowed_domains"] = tuple(allowed)
    return AgentConfig(**payload).validated()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the local evidence-first website discovery agent."
    )
    parser.add_argument("manifest", help="Path to a site-agent JSON manifest")
    parser.add_argument(
        "--provider",
        choices=("llama.cpp", "heuristic"),
        default="llama.cpp",
        help="Reasoning backend. llama.cpp expects a local OpenAI-compatible server.",
    )
    parser.add_argument(
        "--endpoint",
        default="http://127.0.0.1:8080/v1/chat/completions",
        help="Local llama.cpp chat-completions endpoint.",
    )
    parser.add_argument("--model", default="qwen3-4b-instruct", help="Model name sent to the local server")
    args = parser.parse_args()

    config = load_config(args.manifest)
    provider = (
        HeuristicProvider()
        if args.provider == "heuristic"
        else LlamaCppProvider(endpoint=args.endpoint, model=args.model)
    )
    snapshot = SiteDiscoveryAgent(config, provider).run()
    print(f"Discovery complete. Reusable knowledge snapshot: {snapshot}")


if __name__ == "__main__":
    main()
