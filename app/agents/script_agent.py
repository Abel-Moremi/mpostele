"""Script & Layout Agent: generates the spoken script, overlay text, and scene concept."""
from app.agents.base import call_ollama, extract_json
from app.agents.quality_inspector import MAX_OVERLAY_CHARS, MAX_SCRIPT_CHARS
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

PROMPT = """You are a short-form marketing scriptwriter. Given this strategy brief, respond with
ONLY a JSON object with keys "script_text" (<= {max_script_chars} characters), "overlay_text"
(<= {max_overlay_chars} characters), and "scene_concept" (a short visual description). No prose,
no markdown fences.

"script_text" is narration read aloud by a text-to-speech engine - plain words only, never emoji,
hashtags, or markdown. Use close to the full {max_script_chars}-character budget so there's enough
narration to pace a {target_seconds}-second video - a couple of short sentences, not a single
clipped line. Example script_text: "Stop wrestling with setup scripts. Our CLI gets your containers
running in one command, every time, on every machine your team touches - no more onboarding docs
that go stale the week you write them."

Strategy brief:
{strategy_brief}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            max_script_chars=MAX_SCRIPT_CHARS,
            max_overlay_chars=MAX_OVERLAY_CHARS,
            target_seconds=settings.VIDEO_TARGET_DURATION_SECONDS,
            strategy_brief=job_state["strategy_brief"],
        )
    )
    content = extract_json(response)
    state.update(job_id, "content", content, current_step="KEYFRAME_AGENT")


if __name__ == "__main__":
    run(parse_job_arg())
