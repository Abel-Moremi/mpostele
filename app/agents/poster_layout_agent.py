"""Poster Composition Agent: converts the overlay copy into Revideo poster props.

Poster path only - the orchestrator doesn't call this for video jobs. Revideo
handles text wrapping and positioning itself, so unlike the old Pillow-based
version, this prompt needs no canvas dimensions or coordinates - just the
headline, a short CTA label, and two colors. Renders via the fixed
revideo/src/scenes/poster.tsx generator (app/media/poster_engine.py).
"""
from app.agents import brand
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a poster copywriter. Given this overlay text and call to action, respond with
ONLY a JSON object matching this shape. "headline" should be punchy marketing copy drawn from the
overlay text. "ctaText" must be a short label of 2-4 words (like "Run 1-Line Install" or "Download
Now"), never the full call-to-action sentence. Colors and fonts are fixed by the brand elsewhere,
so do not include them. Example shape:
{{
  "headline": "AUTOMATE YOUR STACK",
  "ctaText": "Run 1-Line Install"
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
    # Colors/fonts are a fixed brand identity (design.md), not a per-job
    # creative choice - see app/agents/brand.py.
    poster_layout.update(
        {
            "backgroundColor": brand.BACKGROUND_COLOR,
            "accentColor": brand.ACCENT_COLOR,
            "headlineColor": brand.TEXT_COLOR,
            "ctaTextColor": brand.ON_ACCENT_COLOR,
            "headlineFontFamily": brand.HEADLINE_FONT,
            "ctaFontFamily": brand.BODY_FONT,
        }
    )
    # revideo/src/scenes/poster.tsx has always supported a logoSrc prop too -
    # it just had nothing setting it until now, same gap as the video path's
    # Outro scene (see composition_agent.py's _apply_brand).
    if brand.LOGO_SRC:
        poster_layout["logoSrc"] = brand.LOGO_SRC
    state.update(job_id, "poster_layout", poster_layout, current_step="POSTER_VALIDATOR")


if __name__ == "__main__":
    run(parse_job_arg())
