"""Video rendering engine: Remotion (code-driven motion graphics, no diffusion model).

Runs as its own subprocess, same contract as video_engine.py's run(job_id) -
reads composition_spec from state, shells out to the Remotion CLI in the
sibling remotion/ Node project, and writes the result back to state.
"""
import json
import shutil
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def render(job_state: dict, output_dir: Path) -> Path:
    if not settings.REMOTION_PROJECT_DIR.is_dir():
        raise RuntimeError(
            f"REMOTION_PROJECT_DIR ({settings.REMOTION_PROJECT_DIR}) does not exist. "
            "Run `npm install` inside remotion/ before using --execution-mode remotion."
        )

    # On Windows, npx/npm are .cmd shims - subprocess.run can't exec them
    # directly without shell=True unless resolved to their real path first.
    # shutil.which() does that resolution correctly on every platform.
    node_binary = shutil.which(settings.NODE_BINARY)
    if node_binary is None:
        raise RuntimeError(
            f"NODE_BINARY ({settings.NODE_BINARY!r}) was not found on PATH. "
            "Install Node.js + npm before using --execution-mode remotion."
        )

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "composition_props.json"
    props_path.write_text(json.dumps(job_state["composition_spec"]), encoding="utf-8")

    raw_clip = output_dir / "raw_clip.mp4"
    subprocess.run(
        [
            node_binary,
            "remotion",
            "render",
            settings.REMOTION_COMPOSITION_ID,
            str(raw_clip),
            "--props",
            str(props_path),
        ],
        cwd=settings.REMOTION_PROJECT_DIR,
        check=True,
        timeout=settings.REMOTION_RENDER_TIMEOUT_SECONDS,
    )
    return raw_clip


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    raw_clip = render(job_state, output_dir)

    job_state = state.load(job_id)
    # Straight to "interpolated_clip", skipping the RIFE stage entirely -
    # Remotion renders natively at REMOTION_FPS, so there's no low-frame-count
    # source to upsample the way AnimateDiff/Wan2.1 output needs.
    job_state["artifacts"]["interpolated_clip"] = str(raw_clip)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
