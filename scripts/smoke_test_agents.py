"""Manual smoke test: runs the LLM agent swarm (strategy -> script -> quality
inspector) against a live Ollama server and prints the resulting state.json,
without touching the Remotion render stages.

Usage:
    python scripts/smoke_test_agents.py [path/to/brief.json]
"""
import json
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.orchestrator import state
from app.orchestrator.process_runner import run_stage


def main(brief_path: str) -> None:
    with open(brief_path, "r", encoding="utf-8") as f:
        input_brief = json.load(f)

    job_id = f"job_{uuid.uuid4().hex[:12]}"
    state.create(job_id, "poster", "9:16", input_brief)
    print(f"job: {job_id}")

    run_stage("app.agents.strategy_agent", job_id)
    run_stage("app.agents.script_agent", job_id)

    for attempt in range(settings.MAX_QUALITY_RETRIES + 1):
        result = run_stage("app.agents.quality_inspector", job_id, check_exit_code=False)
        passed = result.returncode == 0
        print(f"quality check attempt {attempt}: {'PASS' if passed else 'FAIL'}")
        if passed or attempt == settings.MAX_QUALITY_RETRIES:
            break
        run_stage("app.agents.script_agent", job_id)

    print(json.dumps(state.load(job_id), indent=2))


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/sample_brief.json")
