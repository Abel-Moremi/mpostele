"""Execution Dispatcher: decides whether the video path renders locally or remotely.

Deterministic routing, not an LLM call - it only needs to know the job's
requested execution_mode and whether a remote endpoint is configured.
"""
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def resolve_target(job_state: dict) -> str:
    if job_state.get("execution_mode") in ("local", "remote"):
        return job_state["execution_mode"]
    return "remote" if settings.WAN21_REMOTE_ENDPOINT else "local"


def run(job_id: str) -> str:
    job_state = state.load(job_id)
    target = resolve_target(job_state)
    state.update(job_id, "dispatch_target", target, current_step="VIDEO_ENGINE")
    return target


if __name__ == "__main__":
    run(parse_job_arg())
