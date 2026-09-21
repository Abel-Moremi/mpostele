"""Composition Director Agent: converts the script into a Revideo scene list.

Video path only - the orchestrator doesn't call this for poster jobs. Produces
data (which fixed scene components to use, in what order, with what
text/colors) - never scene code. The scene generators themselves are
hand-written once in revideo/src/scenes/ and reused across every job; only
this spec is agent-generated, same split as poster_layout_agent's props
versus revideo/src/scenes/poster.tsx's fixed rendering logic.

Scene *duration* is deliberately not part of what the LLM decides (see
_assign_durations) - narration only ever covers CaptionOverlay's script body
(narration_engine.py synthesizes from content.script_text alone), so its
duration is set in Python to exactly match the real synthesized narration
length, and TitleReveal/Outro get fixed silent-title-card beats from
settings.TITLE_REVEAL_SECONDS/OUTRO_HOLD_SECONDS. A small local model guessing
frame counts toward a target was a source of drift (the model has no way to
know real narration length) and exact arithmetic it isn't reliable at
regardless.
"""
from app.agents import brand
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

# Keep in sync with revideo/src/schema.ts's component union and
# app/agents/composition_validator.py's ALLOWED_COMPONENTS.
PROMPT = """You are a video composition director. Given this script hook, script body, and call to
action, respond with ONLY a JSON object matching this shape. Use ONLY these three scene
components, in this order: "TitleReveal" (opens with the hook), "CaptionOverlay" (delivers the
script body as on-screen caption text), "Outro" (closes with the call to action). Colors and fonts
are fixed by the brand elsewhere, so do not include them - only "text". Every "text" value must be
real words copied or adapted from the hook/script body/call to action below - never a placeholder
like "..." or an empty string. Example shape (with placeholder example text your answer must NOT
reuse - fill each "text" from this job's own hook/script body/call to action):
{{
  "scenes": [
    {{"component": "TitleReveal", "props": {{"text": "Stop wrestling with setup scripts"}}}},
    {{"component": "CaptionOverlay",
      "props": {{"text": "Our CLI gets your containers running in one command, every time, on every machine your team touches."}}}},
    {{"component": "Outro", "props": {{"text": "Try our CLI tool today"}}}}
  ]
}}
No prose, no markdown fences.

Script hook: {target_hook}
Script body: {script_text}
Call to action: {call_to_action}
"""

# Component -> fixed duration in seconds, except CaptionOverlay which is set
# per job from the real narration length (see _assign_durations).
_FIXED_SCENE_SECONDS = {
    "TitleReveal": settings.TITLE_REVEAL_SECONDS,
    "Outro": settings.OUTRO_HOLD_SECONDS,
}


def _assign_durations(composition_spec: dict, narration_seconds: float, fps: int) -> None:
    """Injects durationInFrames per scene - deterministic, not agent output
    (see module docstring for why). Leaves durationInFrames unset on any scene
    with an unrecognized component instead of raising: composition_validator.py
    already rejects a missing/non-positive durationInFrames, so a malformed
    LLM scene list still flows through the existing retry-then-fall-through
    gate in orchestrator.py rather than crashing the job outright."""
    for scene in composition_spec.get("scenes", []):
        component = scene.get("component")
        if component == "CaptionOverlay":
            scene["durationInFrames"] = round(narration_seconds * fps)
        elif component in _FIXED_SCENE_SECONDS:
            scene["durationInFrames"] = round(_FIXED_SCENE_SECONDS[component] * fps)


def _apply_brand(composition_spec: dict) -> None:
    """Colors/fonts are a fixed brand identity (design.md's "Warm paper,
    terracotta action"), not a per-job creative choice - overwrite whatever
    the LLM produced (or omitted) rather than trust it, same reasoning
    app/agents/svg_agent.py already applies to decoration colors.

    Outro's text renders inside its terracotta badge/pill, not on the cream
    page background (revideo/src/scenes/outro.tsx) - it needs ink that
    contrasts with ACCENT_COLOR, per design.md's "put white ink on
    terracotta instead". TitleReveal/CaptionOverlay's text sits directly on
    the cream page, so it takes the normal body-text color instead.
    """
    for scene in composition_spec.get("scenes", []):
        props = scene.get("props")
        if not isinstance(props, dict):
            continue
        component = scene.get("component")
        props["backgroundColor"] = brand.BACKGROUND_COLOR
        if component == "CaptionOverlay":
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.BODY_FONT
        elif component == "Outro":
            props["accentColor"] = brand.ACCENT_COLOR
            props["textColor"] = brand.ON_ACCENT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT
        else:
            props["accentColor"] = brand.ACCENT_COLOR
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            target_hook=job_state["strategy_brief"]["target_hook"],
            script_text=job_state["content"]["script_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    composition_spec = extract_json(response)
    _assign_durations(composition_spec, job_state["narration"]["duration_seconds"], settings.REVIDEO_FPS)
    _apply_brand(composition_spec)
    state.update(job_id, "composition_spec", composition_spec, current_step="COMPOSITION_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
