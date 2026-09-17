"""Video rendering engine: local SD1.5 + AnimateDiff fallback, or remote Wan2.1 dispatch.

Runs as its own subprocess; the local branch releases its CUDA context
before this process exits.
"""
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media import memory
from app.orchestrator import state


def render_local(job_state: dict, output_dir: Path) -> Path:
    """SD1.5 + AnimateDiff fallback. Frame count is intentionally conservative
    and not yet validated against real VRAM usage on a 4GB card - see
    docs-mpostele/04 Research/01 Local Diffusion Model Options.md."""
    import torch
    from diffusers import AnimateDiffPipeline, MotionAdapter
    from diffusers.utils import export_to_gif

    adapter = MotionAdapter.from_pretrained(settings.ANIMATEDIFF_MOTION_ADAPTER_ID)
    pipe = AnimateDiffPipeline.from_pretrained(
        settings.SD15_MODEL_ID,
        motion_adapter=adapter,
        torch_dtype=torch.float16,
    ).to("cuda")
    pipe.enable_attention_slicing()

    prompt = job_state["keyframe_prompt"]
    frames = pipe(
        prompt=prompt["positive"],
        negative_prompt=prompt["negative"],
        num_frames=settings.ANIMATEDIFF_FRAME_COUNT,
        num_inference_steps=settings.SD15_STEPS,
    ).frames[0]

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_clip = output_dir / "raw_clip.gif"
    export_to_gif(frames, str(raw_clip))

    del pipe
    memory.flush_cuda_memory()
    return raw_clip


def render_remote(job_state: dict, output_dir: Path) -> Path:
    """Dispatches a Wan2.1 job to a remote runtime.

    Not yet implemented - the actual Colab/Modal/RunPod client contract
    hasn't been decided. Set execution_mode to "local" until this is wired up.
    """
    raise NotImplementedError(
        "Remote Wan2.1 dispatch is not implemented yet. "
        "Set execution_mode to 'local' or implement render_remote() in app/media/video_engine.py."
    )


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    target = job_state.get("dispatch_target", "local")

    if target == "remote":
        raw_clip = render_remote(job_state, output_dir)
    else:
        raw_clip = render_local(job_state, output_dir)

    job_state = state.load(job_id)
    job_state["artifacts"]["raw_clip"] = str(raw_clip)
    job_state["current_step"] = "INTERPOLATION"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
