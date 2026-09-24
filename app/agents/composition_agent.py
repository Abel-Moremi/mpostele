"""Composition Director Agent: converts the script into a Revideo scene list.

Video path only - the orchestrator doesn't call this for poster jobs. Produces
data (which fixed scene components to use, in what order, with what
text/colors/transitions) - never scene code. The scene generators themselves
are hand-written once in revideo/src/scenes/ and reused across every job;
only this spec is agent-generated, same split as poster_layout_agent's props
versus revideo/src/scenes/poster.tsx's fixed rendering logic.

Scene *count*, *duration*, and *text* for CaptionOverlay are deliberately not
part of what the LLM decides (see _build_scenes): narration_engine.py already
splits content.script_text into one real, measured segment per sentence, so
Python builds one CaptionOverlay scene per segment directly from that -
there's nothing left for the LLM to guess. Its only remaining job is
adapting the hook/call-to-action into TitleReveal/Outro's on-screen text.

Transition choice (see _assign_transitions/_propose_transitions) is a
judgment call handed to the creative-tier model, with Python kept as the
safety net that guarantees a valid, non-repeating result regardless of what
the model proposes - so unlike the two text-generation calls above, a bad
proposal here never needs a retry, it just falls back silently.

Which IllustratedExample archetypes to feature (see _choose_archetypes/
_propose_archetypes) is the same shape of judgment call handed to the
creative-tier model, with the same Python safety net - the model picks
*ids* from revideo/public/design/archetypes/manifest.json's fixed, hand-
authored icon set (never invents or draws one, see
revideo/src/scenes/illustrated-example.tsx's module docstring), and a bad or
missing proposal falls back to a deterministic, job_id-seeded pick rather
than blocking the job.
"""
import hashlib
import json
import re

from app.agents import brand
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

_ARCHETYPE_MANIFEST_PATH = settings.REVIDEO_PROJECT_DIR / "public" / "design" / "archetypes" / "manifest.json"
_ARCHETYPE_COUNT = 3

# UI chrome for ProductMockup - fixed copy, not agent data, same status as
# TitleReveal/Outro's decorative shapes (see product-mockup.tsx's own
# docstring: only headline/typedText/items are data, the rest is hand-written).
_MOCKUP_HEADLINE = "What's your story about?"

# Caps for the optional emphasis-word fields below - short enough that
# title-reveal.tsx/outro.tsx's fixed-width underline always reads as "under
# the phrase" (see those files' EMPHASIS_UNDERLINE_WIDTH comment).
_MAX_EMPHASIS_CHARS = 32
_MAX_TAGLINE_CHARS = 60

# PROMPT's own example values below, lowercased - qwen2.5:1.5b has been
# observed echoing these back verbatim for a real brief (e.g. producing the
# literal outro_emphasis "for once." for a bedtime-story-app job that has
# nothing to do with it), the same class of failure composition_validator.py's
# "..." placeholder check already guards against for text/text-like fields.
# Short generic phrases like these are exactly what a small model latches
# onto, so they need an explicit exact-match reject, not just the generic
# "contains a letter" check in _clean_short_text.
_EXAMPLE_PLACEHOLDER_VALUES = {
    "finally.",
    "for once.",
    "let the tool handle the busywork",
    "stop wrestling with setup scripts",
    "try our cli tool today",
}


def _is_example_placeholder(value) -> bool:
    return isinstance(value, str) and value.strip().lower() in _EXAMPLE_PLACEHOLDER_VALUES

PROMPT = """You are a video composition director. Given this campaign's hook and call to action,
respond with ONLY a JSON object with these keys - no prose, no markdown fences:
"title_text": a punchy on-screen adaptation of the hook, opening the video
"title_emphasis": a short (1-3 word) emphasized closing phrase that complements the title, in a
  warm, poetic voice - a single striking word or short exclamation, not a repeat of title_text
"outro_text": a short on-screen adaptation of the call to action, closing the video
"outro_tagline": a short (4-8 word) emotional closing statement, separate from the call to action
"outro_emphasis": a short (1-3 word) emphasized closing phrase that complements outro_tagline

All five must be real words adapted from the hook/call to action below - never a placeholder like
"..." or an empty string. Example shape (placeholder text your answer must NOT reuse):
{{
  "title_text": "Stop wrestling with setup scripts",
  "title_emphasis": "finally.",
  "outro_text": "Try our CLI tool today",
  "outro_tagline": "Let the tool handle the busywork",
  "outro_emphasis": "for once."
}}

Hook: {target_hook}
Call to action: {call_to_action}
"""


def _clean_short_text(value, max_chars: int) -> str:
    """Best-effort sanitization for the optional emphasis/tagline fields -
    "" means "omit this prop entirely", same graceful-degradation pattern
    decorationSrc/logoSrc already use elsewhere. Never raises, never blocks
    the job - a bad or missing value here just means the video plays without
    that one polish detail instead of retrying composition_agent.py over a
    cosmetic phrase."""
    if not isinstance(value, str):
        return ""
    cleaned = value.strip()
    if not cleaned or not re.search(r"[A-Za-z0-9]", cleaned) or len(cleaned) > max_chars:
        return ""
    if _is_example_placeholder(cleaned):
        return ""
    return cleaned

# The Revideo transition library's known transition types
# (revideo/src/transitions.ts) - keep in sync with schema.ts's transitionOut
# enum. Component names below must likewise stay in sync with schema.ts's
# component union and composition_validator.py's ALLOWED_COMPONENTS.
_TRANSITIONS = ["crossfade", "slide", "matchCut"]

TRANSITION_PROMPT = """You are a video editor choosing cut styles. Given this sequence of on-screen
text moments in order, choose one transition for EACH of the {n_cuts} cuts between consecutive
moments. Respond with ONLY a JSON object: {{"transitions": [...]}}, a list of exactly {n_cuts}
values, each one of: crossfade, slide, matchCut. Pick whichever fits that specific cut's mood/pacing
best - crossfade for a calm continuation, slide for an energetic/fast beat, matchCut for a dramatic
or tightly connected idea. No prose, no markdown fences.

Sequence:
{sequence}
"""

ARCHETYPE_PROMPT = """You are a children's-story casting director. Given this campaign's topic, pick exactly
{n} character archetypes from the list below that would make good illustrated examples for a short teaser
about it, and write one short (max 6 words) caption for each in the story's own voice. Respond with ONLY a
JSON object: {{"items": [{{"iconId": "<id>", "caption": "<short phrase>"}}, ...]}}, exactly {n} entries, ids
only from the list below, no prose, no markdown fences.

Available archetypes: {archetype_ids}

Topic: {topic}
"""


def _frames(seconds: float) -> int:
    return round(seconds * settings.REVIDEO_FPS)


def _load_archetypes() -> list:
    return json.loads(_ARCHETYPE_MANIFEST_PATH.read_text(encoding="utf-8"))


def _propose_archetypes(topic: str, archetypes: list) -> list:
    """Best-effort creative-tier proposal - see module docstring. Mirrors
    _propose_transitions's shape exactly: anything that comes back wrong
    (missing, not a list, bad JSON) is treated as absent, never retried."""
    try:
        response = call_ollama(
            ARCHETYPE_PROMPT.format(
                n=_ARCHETYPE_COUNT,
                archetype_ids=[a["id"] for a in archetypes],
                topic=topic,
            ),
            model=settings.OLLAMA_CREATIVE_MODEL,
        )
        proposed = extract_json(response).get("items")
        return proposed if isinstance(proposed, list) else []
    except Exception as exc:
        print(f"Warning: archetype proposal failed, falling back to deterministic picks: {exc}")
        return []


def _choose_archetypes(job_state: dict, job_id: str) -> list:
    """Picks _ARCHETYPE_COUNT archetypes for the IllustratedExample scene.
    _propose_archetypes supplies a creative-tier guess; Python is the safety
    net - deterministic, job_id-seeded (same approach _assign_transitions and
    audio_engine.py's pick_music_track already use) - guaranteeing a valid,
    non-repeating iconId/caption pair for every slot regardless of what (if
    anything) was proposed for it."""
    archetypes = _load_archetypes()
    valid_ids = {a["id"] for a in archetypes}
    topic = job_state.get("strategy_brief", {}).get("topic", "")
    proposed = _propose_archetypes(topic, archetypes)

    seed = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16)
    items = []
    used_ids = set()
    for i in range(_ARCHETYPE_COUNT):
        candidate = proposed[i] if i < len(proposed) else {}
        icon_id = candidate.get("iconId") if isinstance(candidate, dict) else None
        caption = candidate.get("caption") if isinstance(candidate, dict) else None
        valid_caption = isinstance(caption, str) and caption.strip()
        if icon_id not in valid_ids or icon_id in used_ids or not valid_caption:
            choices = [a for a in archetypes if a["id"] not in used_ids]
            chosen = choices[seed % len(choices)]
            seed //= len(choices)
            icon_id, caption = chosen["id"], chosen["label"]
        used_ids.add(icon_id)
        items.append({"iconId": icon_id, "caption": caption.strip()})
    return items


def _scene_summary_text(scene: dict) -> str:
    """_assign_transitions needs one representative string per scene to hand
    the mood-picking prompt - TitleReveal/CaptionOverlay/Outro already have a
    top-level "text" prop, but IllustratedExample (items) and
    AbstractTransition (textless) don't, so this derives a stand-in instead
    of the KeyError a plain props["text"] lookup would hit."""
    props = scene.get("props", {})
    if "text" in props:
        return props["text"]
    items = props.get("items")
    if isinstance(items, list):
        return "; ".join(item.get("caption", "") for item in items if isinstance(item, dict))
    return ""


def _build_typed_text(items: list) -> str:
    """Mechanical assembly, not another LLM call - the captions were already
    chosen by _choose_archetypes, so there's nothing left to generate here,
    same "narration_engine.py already did the real work" reasoning this
    module's own docstring gives for CaptionOverlay's text. This is what
    product-mockup.tsx's simulated input types out, paying the same items
    off a second time (see that file's module docstring)."""
    captions = [item["caption"] for item in items]
    if not captions:
        return ""
    if len(captions) == 1:
        return f"A story about {captions[0]}."
    *head, tail = captions
    return f"A story about {', '.join(head)} and {tail}."


def _build_scenes(
    job_state: dict,
    title_text: str,
    outro_text: str,
    example_items: list,
    title_emphasis: str = "",
    outro_tagline: str = "",
    outro_emphasis: str = "",
) -> list:
    title_props = {"text": title_text}
    if title_emphasis:
        title_props["emphasisText"] = title_emphasis

    outro_props = {"text": outro_text}
    if outro_tagline:
        outro_props["tagline"] = outro_tagline
        if outro_emphasis:
            outro_props["emphasisText"] = outro_emphasis

    scenes = [
        {
            "component": "TitleReveal",
            "durationInFrames": _frames(settings.TITLE_REVEAL_SECONDS),
            "props": title_props,
        },
        {
            "component": "IllustratedExample",
            "durationInFrames": _frames(settings.ILLUSTRATED_EXAMPLE_SECONDS),
            "props": {"items": example_items},
        },
    ]
    for segment in job_state["narration"]["segments"]:
        scenes.append(
            {
                "component": "CaptionOverlay",
                "durationInFrames": _frames(segment["duration_seconds"]),
                "props": {"text": segment["text"]},
            }
        )
    scenes.append(
        {
            "component": "ProductMockup",
            "durationInFrames": _frames(settings.PRODUCT_MOCKUP_SECONDS),
            "props": {
                "headline": _MOCKUP_HEADLINE,
                "typedText": _build_typed_text(example_items),
                "items": example_items,
            },
        }
    )
    scenes.append(
        {
            "component": "BadgeChecklist",
            "durationInFrames": _frames(settings.BADGE_CHECKLIST_SECONDS),
            "props": {"items": example_items},
        }
    )
    scenes.append(
        {
            "component": "AbstractTransition",
            "durationInFrames": _frames(settings.TRANSITION_BEAT_SECONDS),
            "props": {},
        }
    )
    scenes.append(
        {
            "component": "Outro",
            "durationInFrames": _frames(settings.OUTRO_HOLD_SECONDS),
            "props": outro_props,
        }
    )
    return scenes


def _propose_transitions(texts: list, n_cuts: int) -> list:
    """Best-effort creative-tier proposal for which transition fits each
    cut's mood/pacing - _assign_transitions treats anything invalid (wrong
    count, unknown value, a repeat) as absent and falls back to its own
    deterministic pick for that cut, so a failed or nonsensical proposal
    never produces a broken result, just a less creatively-informed one."""
    try:
        sequence = "\n".join(f"{i + 1}. {text}" for i, text in enumerate(texts))
        response = call_ollama(
            TRANSITION_PROMPT.format(n_cuts=n_cuts, sequence=sequence),
            model=settings.OLLAMA_CREATIVE_MODEL,
        )
        proposed = extract_json(response).get("transitions")
        return proposed if isinstance(proposed, list) else []
    except Exception as exc:
        print(f"Warning: transition proposal failed, falling back to deterministic picks: {exc}")
        return []


def _assign_transitions(scenes: list, job_id: str) -> None:
    """Picks a transitionOut for every scene except the last (nothing to
    transition into). _propose_transitions supplies a creative-tier guess
    per cut from each moment's on-screen text; Python is the safety net -
    deterministic, job_id-seeded (same reproducible-but-varied approach
    audio_engine.py's pick_music_track already uses) - guaranteeing every
    cut still gets a *valid*, non-repeating transition regardless of what
    (if anything) was proposed for it."""
    texts = [_scene_summary_text(scene) for scene in scenes]
    proposed = _propose_transitions(texts, len(scenes) - 1)

    seed = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16)
    previous = None
    for i, scene in enumerate(scenes[:-1]):
        candidate = proposed[i] if i < len(proposed) else None
        if candidate not in _TRANSITIONS or candidate == previous:
            choices = [t for t in _TRANSITIONS if t != previous]
            candidate = choices[seed % len(choices)]
            seed //= len(choices)
        scene["transitionOut"] = candidate
        previous = candidate


def _apply_brand(composition_spec: dict) -> None:
    """Colors/fonts are a fixed brand identity (design.md's "Warm paper,
    terracotta action"), not a per-job creative choice - overwrite whatever
    the LLM produced (or omitted) rather than trust it, same reasoning
    app/agents/svg_agent.py already applies to decoration colors.

    Every scene gets accentColor now, not just TitleReveal/Outro - all three
    scene types render a small accent-colored anchor shape that a matchCut
    transition can carry through the cut (see revideo/src/transitions.ts and
    scenes/caption-overlay.tsx's new accent underline).

    Outro's text renders inside its terracotta badge/pill, not on the cream
    page background (revideo/src/scenes/outro.tsx) - it needs ink that
    contrasts with ACCENT_COLOR, per design.md's "put white ink on
    terracotta instead". TitleReveal/CaptionOverlay's text sits directly on
    the cream page, so it takes the normal body-text color instead.

    Outro also gets the brand logo (revideo/src/scenes/outro.tsx has always
    supported a logoSrc prop - it just had nothing setting it until now).

    IllustratedExample/BadgeChecklist/ProductMockup's own text is body-ish
    (captions, chip/window labels), not a headline, so they take the body
    font/color like CaptionOverlay rather than the else-branch's headline
    styling. AbstractTransition is textless and instead needs the two extra
    fixed accent tones its gradient orb cycles through
    (revideo/src/scenes/abstract-transition.tsx). TitleReveal/Outro also get
    that same secondaryColor now - it's what their optional emphasis-word
    treatment gradients into when emphasisText is present (harmless, unused,
    when it isn't - see title-reveal.tsx/outro.tsx). BadgeChecklist's
    checkmarks get confirmColor - design.md: "Sage - confirmations,
    checkmarks" - rather than reusing accentColor's terracotta, which
    design.md reserves for primary actions only.
    """
    for scene in composition_spec.get("scenes", []):
        props = scene.get("props")
        if not isinstance(props, dict):
            continue
        component = scene.get("component")
        props["backgroundColor"] = brand.BACKGROUND_COLOR
        props["accentColor"] = brand.ACCENT_COLOR
        if component in ("CaptionOverlay", "IllustratedExample", "BadgeChecklist", "ProductMockup"):
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.BODY_FONT
            if component == "BadgeChecklist":
                props["confirmColor"] = brand.TERTIARY_ACCENT_COLOR
        elif component == "Outro":
            props["textColor"] = brand.ON_ACCENT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT
            props["secondaryColor"] = brand.SECONDARY_ACCENT_COLOR
            if brand.LOGO_SRC:
                props["logoSrc"] = brand.LOGO_SRC
        elif component == "AbstractTransition":
            props["secondaryColor"] = brand.SECONDARY_ACCENT_COLOR
            props["tertiaryColor"] = brand.TERTIARY_ACCENT_COLOR
        else:
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT
            props["secondaryColor"] = brand.SECONDARY_ACCENT_COLOR


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            target_hook=job_state["strategy_brief"]["target_hook"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    llm_text = extract_json(response)
    example_items = _choose_archetypes(job_state, job_id)
    # title_text/outro_text are required (unlike the emphasis/tagline
    # fields above), so an echoed placeholder can't just be omitted - it's
    # rejected down to "", which composition_validator.py's existing
    # placeholder-text check (no letters/digits) then catches exactly like
    # any other empty/garbled LLM response, driving the orchestrator's
    # normal composition_agent retry rather than silently shipping the
    # PROMPT's own example text into a real video.
    title_text = llm_text.get("title_text", "")
    if _is_example_placeholder(title_text):
        title_text = ""
    outro_text = llm_text.get("outro_text", "")
    if _is_example_placeholder(outro_text):
        outro_text = ""
    scenes = _build_scenes(
        job_state,
        title_text=title_text,
        outro_text=outro_text,
        example_items=example_items,
        title_emphasis=_clean_short_text(llm_text.get("title_emphasis"), _MAX_EMPHASIS_CHARS),
        outro_tagline=_clean_short_text(llm_text.get("outro_tagline"), _MAX_TAGLINE_CHARS),
        outro_emphasis=_clean_short_text(llm_text.get("outro_emphasis"), _MAX_EMPHASIS_CHARS),
    )
    _assign_transitions(scenes, job_id)
    composition_spec = {"scenes": scenes}
    _apply_brand(composition_spec)
    state.update(job_id, "composition_spec", composition_spec, current_step="COMPOSITION_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
