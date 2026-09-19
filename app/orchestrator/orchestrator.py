"""Drives a job through the Sequential Execution Contract end to end.

Agent swarm (strategy -> script -> keyframe -> quality inspector, bounded
retries) -> unload the LLM -> branch by media_type -> platform adaptor ->
cleanup. See docs-mpostele/02 Architecture.md for the full diagram.
"""
import shutil
import uuid

from app.config import settings
from app.media import memory
from app.orchestrator import state
from app.orchestrator.process_runner import run_stage

AGENT_MODULES = {
    "strategy": "app.agents.strategy_agent",
    "script": "app.agents.script_agent",
    "keyframe": "app.agents.keyframe_agent",
    "motion": "app.agents.motion_agent",
    "poster_layout": "app.agents.poster_layout_agent",
    "quality_inspector": "app.agents.quality_inspector",
    "platform_adaptor": "app.agents.platform_adaptor",
    "dispatcher": "app.agents.dispatcher",
    "composition": "app.agents.composition_agent",
    "composition_validator": "app.agents.composition_validator",
}


def run_job(media_type: str, aspect_ratio: str, input_brief: dict, execution_mode: str = "auto") -> str:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    state.create(job_id, media_type, aspect_ratio, execution_mode, input_brief)

    run_stage(AGENT_MODULES["strategy"], job_id)
    run_stage(AGENT_MODULES["script"], job_id)
    run_stage(AGENT_MODULES["keyframe"], job_id)
    _run_quality_gate(job_id)

    memory.unload_ollama_model()

    if media_type == "poster":
        run_stage(AGENT_MODULES["poster_layout"], job_id)
        run_stage("app.media.poster_engine", job_id)
    else:
        run_stage(AGENT_MODULES["dispatcher"], job_id)
        target = state.load(job_id)["dispatch_target"]
        if target == "remotion":
            _run_composition_gate(job_id)
            run_stage("app.media.remotion_engine", job_id)
        else:
            run_stage(AGENT_MODULES["motion"], job_id)
            run_stage("app.media.video_engine", job_id)
            run_stage("app.media.interpolation", job_id)
        run_stage("app.media.encode", job_id)

    run_stage(AGENT_MODULES["platform_adaptor"], job_id)

    job_state = state.load(job_id)
    job_state["status"] = "COMPLETE"
    state.save(job_state)
    _cleanup_intermediates(job_id)
    return job_id


def _run_quality_gate(job_id: str) -> None:
    """Up to MAX_QUALITY_RETRIES re-runs of script+keyframe; falls through
    on the last failure rather than looping forever (AGENTS.md guardrail)."""
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["quality_inspector"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["script"], job_id)
        run_stage(AGENT_MODULES["keyframe"], job_id)


def _run_composition_gate(job_id: str) -> None:
    """Same bounded-retry-then-fall-through shape as _run_quality_gate, but
    re-running composition_agent on a failed composition_validator check."""
    run_stage(AGENT_MODULES["composition"], job_id)
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["composition_validator"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["composition"], job_id)


def _cleanup_intermediates(job_id: str) -> None:
    tmp_dir = settings.TMP_DIR / job_id
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
