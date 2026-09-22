"""Drives a job through the Sequential Execution Contract end to end.

Agent swarm (strategy -> script -> quality inspector, bounded retries) ->
unload the LLM -> branch by media_type -> platform adaptor -> cleanup. Both
branches render via Revideo (headless Chromium), not a diffusion model. See
docs-mpostele/02 Architecture.md for the full diagram.
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
    "quality_inspector": "app.agents.quality_inspector",
    "creative_critic": "app.agents.creative_critic",
    "platform_adaptor": "app.agents.platform_adaptor",
    "poster_layout": "app.agents.poster_layout_agent",
    "poster_validator": "app.agents.poster_validator",
    "composition": "app.agents.composition_agent",
    "composition_validator": "app.agents.composition_validator",
    "svg": "app.agents.svg_agent",
    "svg_validator": "app.agents.svg_validator",
}


def run_job(media_type: str, aspect_ratio: str, input_brief: dict) -> str:
    job_id = f"job_{uuid.uuid4().hex[:12]}"
    state.create(job_id, media_type, aspect_ratio, input_brief)

    run_stage(AGENT_MODULES["strategy"], job_id)
    run_stage(AGENT_MODULES["script"], job_id)
    _run_quality_gate(job_id)
    _run_creative_gate(job_id)

    _run_svg_gate(job_id)

    memory.unload_ollama_model()
    memory.unload_ollama_model(settings.OLLAMA_CREATIVE_MODEL)

    run_stage("app.media.svg_engine", job_id)

    if media_type == "poster":
        _run_poster_gate(job_id)
        run_stage("app.media.poster_engine", job_id)
    else:
        run_stage("app.media.narration_engine", job_id)
        _run_composition_gate(job_id)
        run_stage("app.media.video_engine", job_id)
        run_stage("app.media.audio_engine", job_id)
        run_stage("app.media.encode", job_id)

    run_stage(AGENT_MODULES["platform_adaptor"], job_id)

    job_state = state.load(job_id)
    job_state["status"] = "COMPLETE"
    state.save(job_state)
    _cleanup_intermediates(job_id)
    return job_id


def _run_quality_gate(job_id: str) -> None:
    """Up to MAX_QUALITY_RETRIES re-runs of script; falls through on the
    last failure rather than looping forever (AGENTS.md guardrail)."""
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["quality_inspector"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["script"], job_id)


def _run_creative_gate(job_id: str) -> None:
    """Same bounded-retry-then-fall-through shape as _run_quality_gate, but
    re-running script_agent on a failed creative_critic check (holistic
    "does this read naturally" judgment, not structural limits - runs for
    both poster and video jobs). Not cross-checked against
    quality_inspector.py's own limits afterward - same independent-gates
    shape _run_svg_gate/_run_composition_gate already have."""
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["creative_critic"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["script"], job_id)


def _run_composition_gate(job_id: str) -> None:
    """Same bounded-retry-then-fall-through shape as _run_quality_gate, but
    re-running composition_agent on a failed composition_validator check."""
    run_stage(AGENT_MODULES["composition"], job_id)
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["composition_validator"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["composition"], job_id)


def _run_poster_gate(job_id: str) -> None:
    """Same bounded-retry-then-fall-through shape as _run_quality_gate, but
    re-running poster_layout_agent on a failed poster_validator check."""
    run_stage(AGENT_MODULES["poster_layout"], job_id)
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["poster_validator"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["poster_layout"], job_id)


def _run_svg_gate(job_id: str) -> None:
    """Bounded retries of svg_agent on a failed svg_validator check, same as
    the other gates - but on final failure this falls through to no
    decoration at all, not "render with whatever's there": a missing accent
    is never as severe as bad copy, so it isn't worth risking a broken/
    unvalidated decoration just to have one."""
    run_stage(AGENT_MODULES["svg"], job_id)
    for _ in range(settings.MAX_QUALITY_RETRIES):
        result = run_stage(AGENT_MODULES["svg_validator"], job_id, check_exit_code=False)
        if result.returncode == 0:
            return
        run_stage(AGENT_MODULES["svg"], job_id)
    state.update(job_id, "decoration_spec", {"action": "none"})


def _cleanup_intermediates(job_id: str) -> None:
    tmp_dir = settings.TMP_DIR / job_id
    if tmp_dir.exists():
        shutil.rmtree(tmp_dir)
