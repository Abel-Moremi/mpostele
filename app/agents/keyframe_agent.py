"""Keyframe Prompt Agent: turns the scene concept into a diffusion prompt pair.

Adds a negative-space / text-free constraint when the job is a poster, so
the SD1.5 background leaves room for the Pillow text overlay.
"""
from app.agents.base import call_ollama, extract_json
from app.cli import parse_job_arg
from app.orchestrator import state

PROMPT = """You are a prompt engineer for Stable Diffusion 1.5. Given this scene concept, respond
with ONLY a JSON object with keys "positive" and "negative".

"positive" is a comma-separated list of descriptive tags (not a full sentence).
"negative" is a comma-separated list of short tags to EXCLUDE from the image - never a restated
description of the scene. Example negative: "blurry, low quality, watermark, extra limbs".
{poster_note}
No prose, no markdown fences.

Scene concept: {scene_concept}
Aspect ratio: {aspect_ratio}
"""

POSTER_NOTE = (
    'This is a poster background. The "positive" tag list must include a composition tag for '
    'empty space in the top third, for example: "..., empty space top third, subject centered '
    'lower half, ...". The "negative" tag list must include: "text, watermark, letters, words, '
    'signage, logo".'
)


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    is_poster = job_state["media_type"] == "poster"
    response = call_ollama(
        PROMPT.format(
            poster_note=POSTER_NOTE if is_poster else "",
            scene_concept=job_state["content"]["scene_concept"],
            aspect_ratio=job_state["aspect_ratio"],
        )
    )
    keyframe_prompt = extract_json(response)
    state.update(job_id, "keyframe_prompt", keyframe_prompt, current_step="QUALITY_INSPECTOR")


if __name__ == "__main__":
    run(parse_job_arg())
