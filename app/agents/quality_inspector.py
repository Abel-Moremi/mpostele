"""Quality Inspector Agent: validates generated content against structural constraints.

Deterministic checks rather than another LLM call - the constraints (length
limits, banned terms) are exact rules, not judgment calls. Exits non-zero on
failure so the orchestrator's subprocess check can drive the retry loop.
"""
import re

from app.cli import parse_job_arg
from app.orchestrator import state

MAX_OVERLAY_CHARS = 40
MAX_SCRIPT_CHARS = 330  # scaled with VIDEO_TARGET_DURATION_SECONDS (was 220 chars for a 20s target)

# qwen2.5:1.5b has been observed handing back two alternative pitches
# separated by " / " (e.g. "Option A... / Option B...") instead of picking
# one, for both script_agent.py's own content and (independently)
# strategy_agent.py's target_hook/call_to_action that script_text often
# echoes - it reads as a literal stray "/" once it's on screen or narrated.
# Not a length problem, so it needs its own check. Requires whitespace on
# both sides of the slash, so a genuine "and/or" or "3/4" (no surrounding
# spaces) doesn't trip it. Unlike strategy_agent.py's own _first_alternative
# (which has no retry gate to fall back on), this drives the orchestrator's
# existing script_agent retry instead of silently keeping half the text -
# narration is worth a real second attempt, not a truncation.
_ALTERNATIVES_RE = re.compile(r"\s+/\s+")


def check(job_state: dict) -> list:
    problems = []
    content = job_state.get("content", {})
    overlay = content.get("overlay_text", "")
    script = content.get("script_text", "")

    if len(overlay) > MAX_OVERLAY_CHARS:
        problems.append(f"overlay_text exceeds {MAX_OVERLAY_CHARS} characters ({len(overlay)})")
    if len(script) > MAX_SCRIPT_CHARS:
        problems.append(f"script_text exceeds {MAX_SCRIPT_CHARS} characters ({len(script)})")
    if _ALTERNATIVES_RE.search(overlay):
        problems.append("overlay_text looks like two alternative options separated by a slash, not one")
    if _ALTERNATIVES_RE.search(script):
        problems.append("script_text looks like two alternative options separated by a slash, not one")

    return problems


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "quality_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
