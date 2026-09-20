"""Composition Validator Agent: validates the Remotion scene list before a render is spawned.

Deterministic checks rather than another LLM call, same rationale as
quality_inspector.py and poster_validator.py's equivalent gate on the poster
path. Exits non-zero on failure so the orchestrator's subprocess check can
drive the retry loop.
"""
from app.agents.quality_inspector import MAX_OVERLAY_CHARS, MAX_SCRIPT_CHARS
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

# Keep in sync with remotion/src/schema.ts's component union and
# app/agents/composition_agent.py's PROMPT.
ALLOWED_COMPONENTS = {"TitleReveal", "CaptionOverlay", "Outro"}
REQUIRED_PROPS = {
    "TitleReveal": {"text", "backgroundColor", "accentColor"},
    "CaptionOverlay": {"text", "backgroundColor"},
    "Outro": {"text", "backgroundColor", "accentColor"},
}
MAX_TOTAL_FRAMES = settings.REMOTION_FPS * 20


def check(job_state: dict) -> list:
    problems = []
    spec = job_state.get("composition_spec", {})
    scenes = spec.get("scenes")

    if not isinstance(scenes, list) or not scenes:
        return ["composition_spec.scenes must be a non-empty list"]

    total_frames = 0
    for i, scene in enumerate(scenes):
        component = scene.get("component")
        if component not in ALLOWED_COMPONENTS:
            problems.append(f"scene {i}: unknown component {component!r}")
            continue

        duration = scene.get("durationInFrames")
        if not isinstance(duration, int) or duration <= 0:
            problems.append(f"scene {i}: durationInFrames must be a positive integer, got {duration!r}")
        else:
            total_frames += duration

        props = scene.get("props", {})
        missing = REQUIRED_PROPS[component] - props.keys()
        if missing:
            problems.append(f"scene {i} ({component}): missing props {sorted(missing)}")

        text = props.get("text", "")
        if component == "CaptionOverlay" and len(text) > MAX_SCRIPT_CHARS:
            problems.append(f"scene {i}: text exceeds {MAX_SCRIPT_CHARS} characters ({len(text)})")
        elif component in ("TitleReveal", "Outro") and len(text) > MAX_OVERLAY_CHARS:
            problems.append(f"scene {i}: text exceeds {MAX_OVERLAY_CHARS} characters ({len(text)})")

    if total_frames > MAX_TOTAL_FRAMES:
        problems.append(f"total durationInFrames {total_frames} exceeds cap {MAX_TOTAL_FRAMES}")

    return problems


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "composition_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
