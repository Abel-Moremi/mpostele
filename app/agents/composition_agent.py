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
"""
import hashlib

from app.agents import brand
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

PROMPT = """You are a video composition director. Given this campaign's hook and call to action,
respond with ONLY a JSON object with two keys: "title_text" (a punchy on-screen adaptation of the
hook, opening the video) and "outro_text" (a short on-screen adaptation of the call to action,
closing the video). Both must be real words adapted from the hook/call to action below - never a
placeholder like "..." or an empty string. No prose, no markdown fences. Example shape (placeholder
text your answer must NOT reuse):
{{
  "title_text": "Stop wrestling with setup scripts",
  "outro_text": "Try our CLI tool today"
}}

Hook: {target_hook}
Call to action: {call_to_action}
"""

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


def _frames(seconds: float) -> int:
    return round(seconds * settings.REVIDEO_FPS)


def _build_scenes(job_state: dict, title_text: str, outro_text: str) -> list:
    scenes = [
        {
            "component": "TitleReveal",
            "durationInFrames": _frames(settings.TITLE_REVEAL_SECONDS),
            "props": {"text": title_text},
        }
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
            "component": "Outro",
            "durationInFrames": _frames(settings.OUTRO_HOLD_SECONDS),
            "props": {"text": outro_text},
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
    texts = [scene["props"]["text"] for scene in scenes]
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
    """
    for scene in composition_spec.get("scenes", []):
        props = scene.get("props")
        if not isinstance(props, dict):
            continue
        component = scene.get("component")
        props["backgroundColor"] = brand.BACKGROUND_COLOR
        props["accentColor"] = brand.ACCENT_COLOR
        if component == "CaptionOverlay":
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.BODY_FONT
        elif component == "Outro":
            props["textColor"] = brand.ON_ACCENT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT
            if brand.LOGO_SRC:
                props["logoSrc"] = brand.LOGO_SRC
        else:
            props["textColor"] = brand.TEXT_COLOR
            props["fontFamily"] = brand.HEADLINE_FONT


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            target_hook=job_state["strategy_brief"]["target_hook"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    llm_text = extract_json(response)
    scenes = _build_scenes(
        job_state,
        title_text=llm_text.get("title_text", ""),
        outro_text=llm_text.get("outro_text", ""),
    )
    _assign_transitions(scenes, job_id)
    composition_spec = {"scenes": scenes}
    _apply_brand(composition_spec)
    state.update(job_id, "composition_spec", composition_spec, current_step="COMPOSITION_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
