"""Composition Director Agent: converts the script into a Revideo scene list.

Video path only - the orchestrator doesn't call this for poster jobs. Produces
data (which fixed scene components to use, in what order, for how long, with
what text/colors) - never scene code. The scene generators themselves are
hand-written once in revideo/src/scenes/ and reused across every job; only
this spec is agent-generated, same split as poster_layout_agent's props
versus revideo/src/scenes/poster.tsx's fixed rendering logic.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

# Keep in sync with revideo/src/schema.ts's component union and
# app/agents/composition_validator.py's ALLOWED_COMPONENTS.
PROMPT = """You are a video composition director. Given this script hook, script body, and call to
action, respond with ONLY a JSON object matching this shape. Use ONLY these three scene
components, in this order: "TitleReveal" (opens with the hook), "CaptionOverlay" (delivers the
script body as on-screen caption text), "Outro" (closes with the call to action). Every scene
needs "durationInFrames" as a positive integer - the video renders at exactly {fps} fps. Pace the
three scenes so they together total close to {target_frames} frames (~{target_seconds} seconds) -
that is the standard length, not a maximum to undercut - and never exceed {max_frames} frames.
Give CaptionOverlay most of that time, since it carries the script body. Colors must be hex
strings. Example shape, showing the expected proportions for a {target_seconds}-second video:
{{
  "scenes": [
    {{"component": "TitleReveal", "durationInFrames": 90,
      "props": {{"text": "...", "backgroundColor": "#0B1220", "accentColor": "#2563EB"}}}},
    {{"component": "CaptionOverlay", "durationInFrames": 660,
      "props": {{"text": "...", "backgroundColor": "#0B1220"}}}},
    {{"component": "Outro", "durationInFrames": 150,
      "props": {{"text": "...", "backgroundColor": "#0B1220", "accentColor": "#2563EB"}}}}
  ]
}}
No prose, no markdown fences.

Script hook: {target_hook}
Script body: {script_text}
Call to action: {call_to_action}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    target_frames = settings.REVIDEO_FPS * settings.VIDEO_TARGET_DURATION_SECONDS
    response = call_ollama(
        PROMPT.format(
            fps=settings.REVIDEO_FPS,
            target_frames=target_frames,
            target_seconds=settings.VIDEO_TARGET_DURATION_SECONDS,
            max_frames=target_frames,
            target_hook=job_state["strategy_brief"]["target_hook"],
            script_text=job_state["content"]["script_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    composition_spec = extract_json(response)
    state.update(job_id, "composition_spec", composition_spec, current_step="COMPOSITION_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
