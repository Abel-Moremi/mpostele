"""Poster rendering engine: SD1.5 text-free background + Pillow compositing.

Runs as its own subprocess so the SD1.5 pipeline's CUDA context is released
when this process exits, per the Sequential Execution Contract.
"""
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media import compositor, memory
from app.orchestrator import state


def generate_background(prompt: dict, output_path: Path) -> Path:
    import torch
    from diffusers import StableDiffusionPipeline

    pipe = StableDiffusionPipeline.from_pretrained(
        settings.SD15_MODEL_ID,
        torch_dtype=torch.float16,
        safety_checker=None,
    ).to("cuda")
    pipe.enable_attention_slicing()

    image = pipe(
        prompt=prompt["positive"],
        negative_prompt=prompt["negative"],
        num_inference_steps=settings.SD15_STEPS,
        width=settings.POSTER_GEN_WIDTH,
        height=settings.POSTER_GEN_HEIGHT,
    ).images[0]

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image.save(output_path)

    del pipe
    memory.flush_cuda_memory()
    return output_path


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    raw_background = settings.TMP_DIR / job_id / "background.png"
    generate_background(job_state["keyframe_prompt"], raw_background)

    final_poster = settings.OUTPUT_DIR / job_id / "poster.png"
    compositor.compose_poster(raw_background, job_state["poster_layout"], final_poster, settings.FONT_DIR)

    job_state = state.load(job_id)
    job_state["artifacts"]["raw_background"] = str(raw_background)
    job_state["artifacts"]["final_poster"] = str(final_poster)
    job_state["current_step"] = "PLATFORM_ADAPTOR"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
