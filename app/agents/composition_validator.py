"""Composition Validator Agent: validates the Revideo scene list before a render is spawned.

Deterministic checks rather than another LLM call, same rationale as
quality_inspector.py and poster_validator.py's equivalent gate on the poster
path. Exits non-zero on failure so the orchestrator's subprocess check can
drive the retry loop.
"""
import re

from app.agents.quality_inspector import MAX_OVERLAY_CHARS, MAX_SCRIPT_CHARS
from app.cli import parse_job_arg
from app.orchestrator import state

# Keep in sync with revideo/src/schema.ts's component union and
# app/agents/composition_agent.py's PROMPT.
ALLOWED_COMPONENTS = {"TitleReveal", "CaptionOverlay", "Outro"}
REQUIRED_PROPS = {
    "TitleReveal": {"text", "backgroundColor", "accentColor"},
    "CaptionOverlay": {"text", "backgroundColor"},
    "Outro": {"text", "backgroundColor", "accentColor"},
}
COLOR_PROPS = {"backgroundColor", "accentColor"}

# revideo/src/color.ts's getContrastColor only computes real contrast for a
# strict 6-digit #RRGGBB string - anything else (a CSS name, "#fff", an alpha
# hex) silently falls back to white with no error, which can render invisible
# white-on-white text if the LLM ever emits something other than the exact
# format it's asked for. Rejecting bad colors here, before a render is even
# spawned, is the only real gate on that today.
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def check(job_state: dict) -> list:
    problems = []
    spec = job_state.get("composition_spec", {})
    scenes = spec.get("scenes")

    if not isinstance(scenes, list) or not scenes:
        return ["composition_spec.scenes must be a non-empty list"]

    seen_components = set()
    for i, scene in enumerate(scenes):
        component = scene.get("component")
        if component not in ALLOWED_COMPONENTS:
            problems.append(f"scene {i}: unknown component {component!r}")
            continue
        seen_components.add(component)

        # durationInFrames is assigned deterministically by
        # composition_agent.py's _assign_durations (real narration length for
        # CaptionOverlay, fixed beats for TitleReveal/Outro), not LLM output -
        # this still guards against a scene whose component the LLM produced
        # but _assign_durations couldn't recognize.
        duration = scene.get("durationInFrames")
        if not isinstance(duration, int) or duration <= 0:
            problems.append(f"scene {i}: durationInFrames must be a positive integer, got {duration!r}")

        props = scene.get("props", {})
        missing = REQUIRED_PROPS[component] - props.keys()
        if missing:
            problems.append(f"scene {i} ({component}): missing props {sorted(missing)}")

        for color_prop in COLOR_PROPS & props.keys():
            value = props[color_prop]
            if not isinstance(value, str) or not HEX_COLOR_RE.match(value):
                problems.append(f"scene {i}: {color_prop} must be a 6-digit hex color like #0B1220, got {value!r}")

        text = props.get("text", "")
        if component == "CaptionOverlay" and len(text) > MAX_SCRIPT_CHARS:
            problems.append(f"scene {i}: text exceeds {MAX_SCRIPT_CHARS} characters ({len(text)})")
        elif component in ("TitleReveal", "Outro") and len(text) > MAX_OVERLAY_CHARS:
            problems.append(f"scene {i}: text exceeds {MAX_OVERLAY_CHARS} characters ({len(text)})")

        # The prompt asks for real words, but a small local model has been
        # observed echoing the "..." placeholder from its own example shape
        # back verbatim - reject anything with no actual letters/digits
        # rather than ship a video with blank-looking on-screen text.
        if not isinstance(text, str) or not re.search(r"[A-Za-z0-9]", text):
            problems.append(f"scene {i}: text is empty or placeholder-only ({text!r})")

    # TitleReveal/Outro must each appear at least once - video_engine.py's
    # derive_cover_props() reads the cover image's headline/CTA/colors from
    # exactly these two, and has no data to build a cover without them.
    missing_components = {"TitleReveal", "Outro"} - seen_components
    if missing_components:
        problems.append(f"composition_spec.scenes is missing required component(s) {sorted(missing_components)}")

    return problems


def run(job_id: str) -> bool:
    job_state = state.load(job_id)
    problems = check(job_state)
    passed = not problems
    state.update(job_id, "composition_check", {"passed": passed, "problems": problems})
    return passed


if __name__ == "__main__":
    raise SystemExit(0 if run(parse_job_arg()) else 1)
