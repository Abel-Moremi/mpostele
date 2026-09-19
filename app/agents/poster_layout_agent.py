"""Poster Composition Agent: converts the overlay copy into a structured coordinate map.

Poster path only - the orchestrator doesn't call this for video jobs.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

# The real render is settings.POSTER_GEN_WIDTH/HEIGHT - the LLM has no say
# over canvas size, only over what goes inside it. A first real run gave
# the model a hardcoded 1080x1920 example while actually rendering at
# 512x896: it placed text at x=540 (clipped off the right edge of a 512px-
# wide image) and a badge at y=1600 (entirely below the bottom of an
# 896px-tall image, invisible). Feeding it the true, exact canvas fixes
# that at the source instead of trying to clamp/rescale after the fact.
PROMPT = """You are a poster layout designer. Given this overlay text and call to action, respond
with ONLY a JSON object matching this shape. "font" must always be exactly "Inter-Bold" - it is
the only font file available. The canvas is EXACTLY {canvas_width}x{canvas_height} pixels - every
position and max_width_px must fit inside those bounds, not some other size. The button_badge
"text" must be a short label of 2-4 words (like "Run 1-Line Install" or "Download Now"), never
the full call-to-action sentence. Example for that exact canvas:
{{
  "canvas_size": [{canvas_width}, {canvas_height}],
  "layers": [
    {{"type": "text", "content": "AUTOMATE YOUR STACK", "font": "Inter-Bold", "font_size": 48,
      "max_width_px": {text_max_width}, "color": "#FFFFFF",
      "position": {{"x": {center_x}, "y": {text_y}}}, "align": "center"}},
    {{"type": "button_badge", "text": "Run 1-Line Install", "bg_color": "#2563EB",
      "text_color": "#FFFFFF", "position": {{"x": {center_x}, "y": {badge_y}}}}}
  ]
}}
No prose, no markdown fences.

Overlay text: {overlay_text}
Call to action: {call_to_action}
Aspect ratio: {aspect_ratio}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    canvas_width, canvas_height = settings.POSTER_GEN_WIDTH, settings.POSTER_GEN_HEIGHT
    response = call_ollama(
        PROMPT.format(
            canvas_width=canvas_width,
            canvas_height=canvas_height,
            center_x=canvas_width // 2,
            text_max_width=int(canvas_width * 0.82),
            text_y=int(canvas_height * 0.2),
            badge_y=int(canvas_height * 0.88),
            overlay_text=job_state["content"]["overlay_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
            aspect_ratio=job_state["aspect_ratio"],
        )
    )
    poster_layout = extract_json(response)
    state.update(job_id, "poster_layout", poster_layout, current_step="POSTER_ENGINE")


if __name__ == "__main__":
    run(parse_job_arg())
