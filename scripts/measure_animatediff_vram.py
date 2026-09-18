"""One-off validation: measures actual VRAM usage of the local AnimateDiff
fallback path (app.media.video_engine.render_local) on this GPU.

This resolves the open question flagged in
docs-mpostele/04 Research/01 Local Diffusion Model Options.md - not a unit
test, just a probe to replace "unvalidated" with real numbers.
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import torch

from app.config import settings
from app.media.video_engine import render_local


def gpu_memory_used_mib() -> int:
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
        check=True,
    )
    return int(out.stdout.strip().splitlines()[0])


def main() -> None:
    print(f"GPU memory used before loading anything: {gpu_memory_used_mib()} MiB")
    print(f"ANIMATEDIFF_FRAME_COUNT = {settings.ANIMATEDIFF_FRAME_COUNT}")
    print(f"SD15_STEPS = {settings.SD15_STEPS}")

    torch.cuda.reset_peak_memory_stats()

    job_state = {
        "keyframe_prompt": {
            "positive": "modern developer workspace, laptop, clean desk, soft lighting",
            "negative": "text, watermark, blurry, low quality",
        }
    }
    output_dir = settings.TMP_DIR / "vram_probe"

    raw_clip = render_local(job_state, output_dir)

    peak_allocated = torch.cuda.max_memory_allocated() / (1024**2)
    peak_reserved = torch.cuda.max_memory_reserved() / (1024**2)
    print(f"torch peak allocated : {peak_allocated:.0f} MiB")
    print(f"torch peak reserved  : {peak_reserved:.0f} MiB")
    print(f"nvidia-smi memory.used after run: {gpu_memory_used_mib()} MiB")
    print(f"output clip: {raw_clip}")


if __name__ == "__main__":
    main()
