"""Poster Composition Agent: converts the overlay copy into Remotion poster props.

Poster path only - the orchestrator doesn't call this for video jobs. Remotion/CSS
handles text wrapping and positioning itself, so unlike the old Pillow-based
version, this prompt needs no canvas dimensions or coordinates - just the
headline, a short CTA label, and two colors. Renders via the fixed
remotion/src/scenes/Poster.tsx component (app/media/poster_engine.py).
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a poster copywriter and colorist. Given this overlay text and call to action,
respond with ONLY a JSON object matching this shape. "ctaText" must be a short label of 2-4 words
(like "Run 1-Line Install" or "Download Now"), never the full call-to-action sentence. Colors must
be hex strings that contrast well against white text. Example shape:
{{
  "headline": "AUTOMATE YOUR STACK",
  "ctaText": "Run 1-Line Install",
  "backgroundColor": "#0B1220",
  "accentColor": "#2563EB"
}}
No prose, no markdown fences.

Overlay text: {overlay_text}
Call to action: {call_to_action}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            overlay_text=job_state["content"]["overlay_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
        )
    )
    poster_layout = extract_json(response)
    state.update(job_id, "poster_layout", poster_layout, current_step="POSTER_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
