"""Quality Inspector Agent: validates generated content against structural constraints.

Deterministic checks rather than another LLM call - the constraints (length
limits, banned terms) are exact rules, not judgment calls. Exits non-zero on
failure so the orchestrator's subprocess check can drive the retry loop.
"""
from app.cli import parse_job_arg
from app.orchestrator import state

MAX_OVERLAY_CHARS = 40
MAX_SCRIPT_CHARS = 220


def check(job_state: dict) -> list:
    problems = []
    content = job_state.get("content", {})
    overlay = content.get("overlay_text", "")
    script = content.get("script_text", "")

    if len(overlay) > MAX_OVERLAY_CHARS:
        problems.append(f"overlay_text exceeds {MAX_OVERLAY_CHARS} characters ({len(overlay)})")
    if len(script) > MAX_SCRIPT_CHARS:
        problems.append(f"script_text exceeds {MAX_SCRIPT_CHARS} characters ({len(script)})")

    keyframe = job_state.get("keyframe_prompt", {})
    if job_state.get("media_type") == "poster" and "text" not in keyframe.get("negative", "").lower():
        problems.append("poster negative prompt must exclude rendered text")

    return problems


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "quality_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
