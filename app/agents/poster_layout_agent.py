"""Poster Composition Agent: converts the overlay copy into a structured coordinate map.

Poster path only - the orchestrator doesn't call this for video jobs.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a poster layout designer. Given this overlay text and call to action, respond
with ONLY a JSON object matching this shape:
{{
  "canvas_size": [width, height],
  "layers": [
    {{"type": "text", "content": str, "font": str, "font_size": int, "max_width_px": int,
      "color": "#RRGGBB", "position": {{"x": int, "y": int}}, "align": "center"}},
    {{"type": "button_badge", "text": str, "bg_color": "#RRGGBB", "text_color": "#RRGGBB",
      "position": {{"x": int, "y": int}}}}
  ]
}}
No prose, no markdown fences.

Overlay text: {overlay_text}
Call to action: {call_to_action}
Aspect ratio: {aspect_ratio}
"""


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    response = call_ollama(
        PROMPT.format(
            overlay_text=job_state["content"]["overlay_text"],
            call_to_action=job_state["strategy_brief"]["call_to_action"],
            aspect_ratio=job_state["aspect_ratio"],
        )
    )
    poster_layout = extract_json(response)
    state.update(job_id, "poster_layout", poster_layout, current_step="POSTER_ENGINE")


if __name__ == "__main__":
    run(parse_job_arg())
