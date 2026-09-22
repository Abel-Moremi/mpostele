"""Strategy & Trend Agent: turns campaign inputs into a target hook and CTA."""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

PROMPT = """You are a marketing strategist. Given this campaign brief, respond with ONLY a JSON
object with keys "topic", "target_hook", and "call_to_action". No prose, no markdown fences.

Campaign brief:
{brief}
"""

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
    response = call_ollama(PROMPT.format(brief=job_state["input_brief"]))
    strategy_brief = extract_json(response)

    if job_state["media_type"] != "poster":
        mood = _tag_mood(job_state["input_brief"])
        if mood:
            strategy_brief["mood"] = mood

    state.update(job_id, "strategy_brief", strategy_brief, current_step="SCRIPT_AGENT")


if __name__ == "__main__":
    run(parse_job_arg())
