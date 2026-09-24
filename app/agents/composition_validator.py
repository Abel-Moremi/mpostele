"""Composition Validator Agent: validates the Revideo scene list before a render is spawned.

Deterministic checks rather than another LLM call, same rationale as
quality_inspector.py and poster_validator.py's equivalent gate on the poster
path. Exits non-zero on failure so the orchestrator's subprocess check can
drive the retry loop.
"""
import json
import re

from app.agents.quality_inspector import MAX_OVERLAY_CHARS, MAX_SCRIPT_CHARS
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

# Keep in sync with revideo/src/schema.ts's component union and
# app/agents/composition_agent.py's PROMPT.
ALLOWED_COMPONENTS = {
    "TitleReveal",
    "CaptionOverlay",
    "Outro",
    "IllustratedExample",
    "AbstractTransition",
    "BadgeChecklist",
    "ProductMockup",
}
REQUIRED_PROPS = {
    "TitleReveal": {"text", "backgroundColor", "accentColor"},
    "CaptionOverlay": {"text", "backgroundColor", "accentColor"},
    "Outro": {"text", "backgroundColor", "accentColor"},
    "IllustratedExample": {"items", "backgroundColor", "accentColor"},
    "AbstractTransition": {"backgroundColor", "accentColor", "secondaryColor", "tertiaryColor"},
    "BadgeChecklist": {"items", "backgroundColor", "accentColor"},
    "ProductMockup": {"headline", "typedText", "items", "backgroundColor", "accentColor"},
}
COLOR_PROPS = {"backgroundColor", "accentColor", "secondaryColor", "tertiaryColor"}
# Components whose "items" list gets reused verbatim across scenes (see
# app/agents/composition_agent.py's _choose_archetypes) - IllustratedExample,
# BadgeChecklist, and ProductMockup's chips all share the exact same
# {iconId, caption} shape, so they share one check rather than three copies.
_ITEMS_COMPONENTS = {"IllustratedExample", "BadgeChecklist", "ProductMockup"}

# IllustratedExample's items[].iconId must be one of these - the fixed,
# hand-authored icon set app/agents/composition_agent.py's _choose_archetypes
# already constrains its own proposal to (see that module's docstring); this
# is the last check before a render is spawned, same role HEX_COLOR_RE plays
# for colors below.
_ARCHETYPE_MANIFEST_PATH = settings.REVIDEO_PROJECT_DIR / "public" / "design" / "archetypes" / "manifest.json"
_VALID_ARCHETYPE_IDS = {
    a["id"] for a in json.loads(_ARCHETYPE_MANIFEST_PATH.read_text(encoding="utf-8"))
}
MAX_EXAMPLE_ITEMS = 3

# revideo/src/color.ts's getContrastColor only computes real contrast for a
# strict 6-digit #RRGGBB string - anything else (a CSS name, "#fff", an alpha
# hex) silently falls back to white with no error, which can render invisible
# white-on-white text if the LLM ever emits something other than the exact
# format it's asked for. Rejecting bad colors here, before a render is even
# spawned, is the only real gate on that today.
HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


def _check_items(problems: list, scene_index: int, items) -> None:
    """Shared by every component in _ITEMS_COMPONENTS - see that set's
    comment. iconId must be a real archetype (the fixed, hand-authored icon
    library composition_agent.py's _choose_archetypes already constrains
    itself to); caption follows the same length/placeholder rules as any
    other on-screen text below."""
    if not isinstance(items, list) or not (1 <= len(items) <= MAX_EXAMPLE_ITEMS):
        problems.append(f"scene {scene_index}: items must be a list of 1 to {MAX_EXAMPLE_ITEMS} entries, got {items!r}")
        return
    for j, item in enumerate(items):
        if not isinstance(item, dict):
            problems.append(f"scene {scene_index} item {j}: must be an object, got {item!r}")
            continue
        icon_id = item.get("iconId")
        if icon_id not in _VALID_ARCHETYPE_IDS:
            problems.append(f"scene {scene_index} item {j}: unknown iconId {icon_id!r}")
        caption = item.get("caption")
        if not isinstance(caption, str) or not caption.strip():
            problems.append(f"scene {scene_index} item {j}: caption is empty or placeholder-only ({caption!r})")
        elif len(caption) > MAX_OVERLAY_CHARS:
            problems.append(f"scene {scene_index} item {j}: caption exceeds {MAX_OVERLAY_CHARS} characters ({len(caption)})")


def _check_text_field(problems: list, scene_index: int, value, field_name: str, max_chars: int) -> None:
    """One on-screen text field's length/placeholder rules - the same two
    checks the old inline "text" handling below applied, generalized so
    emphasisText/tagline/headline/typedText (present some, always else
    optional) can reuse it instead of duplicating the logic per field."""
    if not isinstance(value, str) or not re.search(r"[A-Za-z0-9]", value):
        problems.append(f"scene {scene_index}: {field_name} is empty or placeholder-only ({value!r})")
    elif len(value) > max_chars:
        problems.append(f"scene {scene_index}: {field_name} exceeds {max_chars} characters ({len(value)})")


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

        # IllustratedExample/BadgeChecklist/ProductMockup (items, see
        # _ITEMS_COMPONENTS) and AbstractTransition (no on-screen text at
        # all) don't have a top-level "text" prop - the generic text check
        # below would either KeyError-equivalent (via .get defaulting to
        # "") and wrongly flag them as placeholder-only, or simply not
        # apply. Validate their own fields here instead and skip past the
        # generic text check entirely for all of them.
        if component in _ITEMS_COMPONENTS:
            _check_items(problems, i, props.get("items"))
            if component == "ProductMockup":
                _check_text_field(problems, i, props.get("headline"), "headline", MAX_OVERLAY_CHARS)
                _check_text_field(problems, i, props.get("typedText"), "typedText", MAX_SCRIPT_CHARS)
            continue

        if component == "AbstractTransition":
            continue

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

        # emphasisText (TitleReveal/Outro) and tagline (Outro only) are
        # optional - composition_agent.py's _clean_short_text already omits
        # them entirely rather than ever emitting an empty/placeholder value,
        # but this is the last check before a render is spawned, same
        # defense-in-depth reasoning HEX_COLOR_RE gets applied uniformly
        # rather than trusting whichever stage happened to run first.
        if "emphasisText" in props:
            _check_text_field(problems, i, props.get("emphasisText"), "emphasisText", MAX_OVERLAY_CHARS)
        if "tagline" in props:
            _check_text_field(problems, i, props.get("tagline"), "tagline", MAX_OVERLAY_CHARS)

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
