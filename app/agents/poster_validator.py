"""Poster Validator Agent: validates Revideo poster props before a render is spawned.

Deterministic checks rather than another LLM call, same rationale as
quality_inspector.py/composition_validator.py. Exits non-zero on failure so
the orchestrator's subprocess check can drive the retry loop.
"""
import re

from app.agents.quality_inspector import MAX_OVERLAY_CHARS
from app.cli import parse_job_arg
from app.orchestrator import state

REQUIRED_KEYS = {"headline", "ctaText", "backgroundColor", "accentColor"}
COLOR_KEYS = {"backgroundColor", "accentColor"}
MAX_CTA_CHARS = 40

# See app/agents/composition_validator.py's HEX_COLOR_RE for why this exists -
# same gap, same fix, on the poster path's two colors.
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def check(job_state: dict) -> list:
    problems = []
    layout = job_state.get("poster_layout", {})

    missing = REQUIRED_KEYS - layout.keys()
    if missing:
        problems.append(f"poster_layout missing keys {sorted(missing)}")

    for color_key in COLOR_KEYS & layout.keys():
        value = layout[color_key]
        if not isinstance(value, str) or not HEX_COLOR_RE.match(value):
            problems.append(f"{color_key} must be a 6-digit hex color like #0B1220, got {value!r}")

    headline = layout.get("headline", "")
    if len(headline) > MAX_OVERLAY_CHARS:
        problems.append(f"headline exceeds {MAX_OVERLAY_CHARS} characters ({len(headline)})")

    cta_text = layout.get("ctaText", "")
    if len(cta_text) > MAX_CTA_CHARS:
        problems.append(f"ctaText exceeds {MAX_CTA_CHARS} characters ({len(cta_text)})")

    return problems


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "poster_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
