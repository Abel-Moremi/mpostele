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
    """SD1.5 + AnimateDiff fallback - NOT CONFIRMED VIABLE on this hardware.

    Three configurations measured on the actual 1050 Ti; none genuinely fit
    within 4GB VRAM / 8GB RAM at any frame count tried (4 or 16). See
    docs-mpostele/04 Research/01 Local Diffusion Model Options.md for the
    full comparison. Kept as attention-slicing-only + .to("cuda") here
    because it's the configuration that fails with a clean, catchable
    torch.OutOfMemoryError rather than an unrecoverable segfault
    (enable_model_cpu_offload()) or a ~150s/step silent VRAM-to-RAM spill
    that isn't really "fitting" despite not crashing (.to("cuda") at 4 frames).
    """
    import torch
    from diffusers import AnimateDiffPipeline, MotionAdapter
    from diffusers.utils import export_to_gif

    adapter = MotionAdapter.from_pretrained(settings.ANIMATEDIFF_MOTION_ADAPTER_ID)
    pipe = AnimateDiffPipeline.from_pretrained(
        settings.SD15_MODEL_ID,
        motion_adapter=adapter,
        torch_dtype=torch.float16,
    )
    pipe.enable_attention_slicing()
    pipe.unet.enable_forward_chunking()
    pipe.to("cuda")

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
    """Dispatches a Wan2.1 job to a Colab-hosted server.

    Colab has no official job-submission API. This talks to a small
    FastAPI server that must be started manually inside
    colab/wan21_server.ipynb and exposed via ngrok - copy its printed URL
    into WAN21_REMOTE_ENDPOINT before running a remote job. The URL changes
    every time that notebook restarts.
    """
    import time

    import requests

    if not settings.WAN21_REMOTE_ENDPOINT:
        raise RuntimeError(
            "WAN21_REMOTE_ENDPOINT is not set. Start colab/wan21_server.ipynb, copy its "
            "printed ngrok URL, and set WAN21_REMOTE_ENDPOINT (and WAN21_API_KEY) to match."
        )

    endpoint = settings.WAN21_REMOTE_ENDPOINT.rstrip("/")
    headers = {"x-api-key": settings.WAN21_API_KEY}
    prompt = job_state["keyframe_prompt"]

    submit = requests.post(
        f"{endpoint}/generate",
        json={
            "positive": prompt["positive"],
            "negative": prompt.get("negative", ""),
            "num_frames": settings.WAN21_FRAME_COUNT,
            "width": settings.WAN21_WIDTH,
            "height": settings.WAN21_HEIGHT,
        },
        headers=headers,
        timeout=30,
    )
    submit.raise_for_status()
    remote_job_id = submit.json()["job_id"]

    deadline = time.monotonic() + settings.WAN21_POLL_TIMEOUT_SECONDS
    while True:
        try:
            status_resp = requests.get(f"{endpoint}/status/{remote_job_id}", headers=headers, timeout=30)
            status_resp.raise_for_status()
            status = status_resp.json()
        except (requests.exceptions.ConnectionError, requests.exceptions.Timeout):
            # The ngrok tunnel drops connections transiently while the worker
            # thread is busy loading/running the model - a network blip here
            # doesn't mean the job failed, just retry within the deadline.
            if time.monotonic() > deadline:
                raise
            time.sleep(settings.WAN21_POLL_INTERVAL_SECONDS)
            continue
        except requests.exceptions.HTTPError as exc:
            # A 502/503/504 from ngrok (tunnel up, backend momentarily
            # unreachable) is the same transient case as above - raise_for_status()
            # doesn't raise ConnectionError for these, it raises HTTPError.
            if exc.response is not None and exc.response.status_code in (502, 503, 504) and time.monotonic() <= deadline:
                time.sleep(settings.WAN21_POLL_INTERVAL_SECONDS)
                continue
            raise

        if status["status"] == "done":
            break
        if status["status"] == "error":
            raise RuntimeError(f"Remote Wan2.1 job {remote_job_id} failed: {status['error']}")
        if time.monotonic() > deadline:
            raise TimeoutError(
                f"Remote Wan2.1 job {remote_job_id} did not finish within "
                f"{settings.WAN21_POLL_TIMEOUT_SECONDS}s"
            )
        time.sleep(settings.WAN21_POLL_INTERVAL_SECONDS)

    result_resp = requests.get(f"{endpoint}/result/{remote_job_id}", headers=headers, timeout=120)
    result_resp.raise_for_status()

    output_dir.mkdir(parents=True, exist_ok=True)
    raw_clip = output_dir / "raw_clip.mp4"
    raw_clip.write_bytes(result_resp.content)
    return raw_clip


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
