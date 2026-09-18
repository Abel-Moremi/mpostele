"""Script & Layout Agent: generates the spoken script, overlay text, and scene concept."""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a short-form marketing scriptwriter. Given this strategy brief, respond with
ONLY a JSON object with keys "script_text" (<= 220 characters), "overlay_text" (<= 40 characters),
and "scene_concept" (a short visual description). No prose, no markdown fences.

"script_text" is narration read aloud by a text-to-speech engine - plain words only, never emoji,
hashtags, or markdown. Example script_text: "Stop wrestling with setup scripts. Our CLI gets your
containers running in one command."

Strategy brief:
{strategy_brief}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(PROMPT.format(strategy_brief=job_state["strategy_brief"]))
    content = extract_json(response)
    state.update(job_id, "content", content, current_step="KEYFRAME_AGENT")


if __name__ == "__main__":
    run(parse_job_arg())
