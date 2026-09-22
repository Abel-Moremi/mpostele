"""Creative Critic Agent: holistic judgment on whether the hook, script body,
and call to action read naturally and cohere as one message.

The judgment counterpart to quality_inspector.py's structural checks (length
limits) - "does this read as professional" isn't a rule qwen2.5:1.5b is a
reliable judge of, so this runs on the larger settings.OLLAMA_CREATIVE_MODEL
instead. Runs for both poster and video jobs - script_agent.py's output
(strategy_brief/content) is media-type-agnostic. Exits non-zero on failure so
the orchestrator's subprocess check can drive the retry loop back to
script_agent.py, same shape as quality_inspector.py's gate.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

PROMPT = """You are a critical marketing editor. Given this hook, script body, and call to action,
judge whether they read naturally and cohere as one message - not whether they're perfect, just
whether they'd embarrass a real brand (robotic phrasing, the call to action ignoring the hook,
repeating the same phrase, etc). Respond with ONLY a JSON object: {{"passed": true or false,
"problems": [...]}} - "problems" is a list of specific short issues if passed is false, or an empty
list if passed is true. No prose, no markdown fences.

Hook: {target_hook}
Script body: {script_text}
Call to action: {call_to_action}
"""


def check(job_state: dict) -> list:
    """Best-effort - a creative-model failure (unavailable, timeout, bad
    JSON) degrades to a pass rather than blocking the job: this is a quality
    bar on top of quality_inspector.py's structural gate, not a correctness
    dependency the job can't ship without."""
    strategy_brief = job_state["strategy_brief"]
    content = job_state["content"]
    try:
        response = call_ollama(
            PROMPT.format(
                target_hook=strategy_brief["target_hook"],
                script_text=content["script_text"],
                call_to_action=strategy_brief["call_to_action"],
            ),
            model=settings.OLLAMA_CREATIVE_MODEL,
        )
        result = extract_json(response)
        if result.get("passed", True):
            return []
        problems = result.get("problems") or ["creative_critic flagged this content without giving a reason"]
        return list(problems)
    except Exception as exc:
        print(f"Warning: creative critic check failed, treating as pass: {exc}")
        return []


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "creative_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
