"""The state.json contract: every stage reads and appends to this file
instead of passing data in memory (docs-mpostele/03 Workflow/01 Agent Pipeline Swarm.md).
"""
import json
from pathlib import Path
from typing import Any

from app.config import settings


def state_path(job_id: str) -> Path:
    return settings.JOBS_DIR / job_id / "state.json"


def create(
    job_id: str,
    media_type: str,
    aspect_ratio: str,
    input_brief: dict,
    publish_now: bool = False,
) -> dict:
    job_state = {
        "job_id": job_id,
        "media_type": media_type,
        "aspect_ratio": aspect_ratio,
        "status": "PROCESSING",
        "current_step": "STRATEGY_AGENT",
        "input_brief": input_brief,
        # Set at creation, not by publish_engine.py itself, so the flag is
        # already on disk by the time that stage's subprocess reads state.json.
        "publish_now": publish_now,
        "publish_status": None,
        "artifacts": {
            "final_poster": None,
            "rendered_video": None,
            "cover_image": None,
        },
    }
    save(job_state)
    return job_state


def load(job_id: str) -> dict:
    with open(state_path(job_id), "r", encoding="utf-8") as f:
        return json.load(f)


def save(job_state: dict) -> None:
    path = state_path(job_state["job_id"])
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(job_state, f, indent=2)


def update(
    job_id: str,
    key: str,
    value: Any,
    current_step: str = None,
    status: str = None,
) -> dict:
    job_state = load(job_id)
    job_state[key] = value
    if current_step:
        job_state["current_step"] = current_step
    if status:
        job_state["status"] = status
    save(job_state)
    return job_state
