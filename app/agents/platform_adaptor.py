"""Platform Adaptor Agent: reformats the script into platform-native copy."""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a social media copywriter. Given this script and call to action, respond with
ONLY a JSON object with keys "tiktok", "instagram", "x", and "linkedin", each a short caption
tailored to that platform's tone. No prose, no markdown fences.

Script: {script_text}
Call to action: {call_to_action}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            script_text=job_state["content"]["script_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    platform_copy = extract_json(response)
    state.update(job_id, "platform_copy", platform_copy)


if __name__ == "__main__":
    run(parse_job_arg())
