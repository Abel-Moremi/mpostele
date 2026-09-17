"""Strategy & Trend Agent: turns campaign inputs into a target hook and CTA."""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a marketing strategist. Given this campaign brief, respond with ONLY a JSON
object with keys "topic", "target_hook", and "call_to_action". No prose, no markdown fences.

Campaign brief:
{brief}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(PROMPT.format(brief=job_state["input_brief"]))
    strategy_brief = extract_json(response)
    state.update(job_id, "strategy_brief", strategy_brief, current_step="SCRIPT_AGENT")


if __name__ == "__main__":
    run(parse_job_arg())
