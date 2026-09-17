"""Motion Director Agent: converts the script hook into a camera movement prompt.

Video path only - the orchestrator doesn't call this for poster jobs.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a motion director for a short AI-generated video clip. Given this script hook,
respond with ONLY a JSON object with keys "camera_movement" and "pacing_notes". No prose, no
markdown fences.

Script hook: {target_hook}
Scene concept: {scene_concept}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            target_hook=job_state["strategy_brief"]["target_hook"],
            scene_concept=job_state["content"]["scene_concept"],
        )
    )
    motion_prompt = extract_json(response)
    state.update(job_id, "motion_prompt", motion_prompt, current_step="DISPATCHER")


if __name__ == "__main__":
    run(parse_job_arg())
