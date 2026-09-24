"""Strategy & Trend Agent: turns campaign inputs into a target hook and CTA."""
import re
from pathlib import Path

from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

PROMPT = """You are a marketing strategist. Given the product brief and campaign brief below,
respond with ONLY a JSON object with keys "topic", "target_hook", and "call_to_action". No prose,
no markdown fences.

"target_hook" and "call_to_action" must each be exactly ONE hook and ONE call to action - never two
alternative options separated by a slash, "or", or a line break. Pick the single strongest version
yourself rather than handing back a choice.

Product brief:
{product_brief}

Campaign brief:
{brief}
"""

# qwen2.5:1.5b has been observed ignoring the "exactly ONE" instruction
# above and handing back two alternative hooks/CTAs separated by " / "
# (e.g. "Option A... / Option B..."), which then reads as a literal stray
# "/" once it reaches on-screen text downstream (script_agent.py's
# script_text/overlay_text, composition_agent.py's title_text/outro_text).
# Not caught by any length/placeholder check since it's real, well-formed
# text - just two ideas where one was asked for. This is the deterministic
# safety net, same "Python cleans up what the model actually returns"
# pattern composition_agent.py's _clean_short_text/_choose_archetypes
# already use. Requires whitespace on both sides of the slash, so a
# genuine "and/or" or "3/4" (no surrounding spaces) is left untouched.
_ALTERNATIVES_SPLIT_RE = re.compile(r"\s+/\s+")


def _first_alternative(value):
    if not isinstance(value, str):
        return value
    parts = _ALTERNATIVES_SPLIT_RE.split(value, maxsplit=1)
    return parts[0].strip() if len(parts) > 1 else value

# Video path only (see run()) - keep in sync with settings.MUSIC_MOODS and
# the three placeholder tracks in app/media/music/. Deliberately a separate
# call from PROMPT above, on the creative-tier model, rather than folding
# "mood" into that call's own JSON shape - keeps the existing hook/CTA
# generation completely untouched, on the model it was already tuned against.
MOOD_PROMPT = """You are a music supervisor. Given this campaign brief, respond with ONLY a JSON
object with one key "mood", whose value is exactly one of: {moods}. No prose, no markdown fences.

Campaign brief:
{brief}
"""


def _load_product_brief() -> str:
    """Best-effort, same degradation shape as _tag_mood below - a missing or
    unreadable product_brief.md shouldn't crash the pipeline's first stage,
    it should just fall back to campaign-brief-only strategy generation."""
    try:
        return Path(settings.PRODUCT_BRIEF_PATH).read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Warning: product brief unavailable, continuing without it: {exc}")
        return ""


def _tag_mood(input_brief: dict) -> str:
    """Best-effort - strategy_agent.py is the pipeline's first stage and
    isn't behind a retry gate the way script_agent.py is (run_stage here
    uses check_exit_code=True), so an unhandled failure would crash the
    whole job. A slow/unavailable creative-tier model instead degrades to
    no mood tag - audio_engine.py's pick_music_track already falls back to
    its job_id hash cleanly when mood is missing, same proportionate-
    degradation shape as the SVG decoration gate falling back to none."""
    try:
        response = call_ollama(
            MOOD_PROMPT.format(moods=", ".join(settings.MUSIC_MOODS), brief=input_brief),
            model=settings.OLLAMA_CREATIVE_MODEL,
        )
        mood = extract_json(response).get("mood")
        return mood if mood in settings.MUSIC_MOODS else None
    except Exception as exc:
        print(f"Warning: mood tagging failed, continuing without a mood tag: {exc}")
        return None


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(product_brief=_load_product_brief(), brief=job_state["input_brief"])
    )
    strategy_brief = extract_json(response)
    if "target_hook" in strategy_brief:
        strategy_brief["target_hook"] = _first_alternative(strategy_brief["target_hook"])
    if "call_to_action" in strategy_brief:
        strategy_brief["call_to_action"] = _first_alternative(strategy_brief["call_to_action"])

    if job_state["media_type"] != "poster":
        mood = _tag_mood(job_state["input_brief"])
        if mood:
            strategy_brief["mood"] = mood

    state.update(job_id, "strategy_brief", strategy_brief, current_step="SCRIPT_AGENT")


if __name__ == "__main__":
    run(parse_job_arg())
