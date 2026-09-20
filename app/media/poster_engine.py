"""Poster rendering engine: Remotion still render (code-driven, no diffusion model).

Runs as its own subprocess - reads poster_layout from state, shells out to
the Remotion CLI's single-frame `still` render, and writes the result back
to state. Mirrors video_engine.py's subprocess pattern exactly.
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
            "Run `npm install` inside remotion/ first."
        )

    node_binary = shutil.which(settings.NODE_BINARY)
    if node_binary is None:
        raise RuntimeError(f"NODE_BINARY ({settings.NODE_BINARY!r}) was not found on PATH. Install Node.js + npm.")

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "poster_props.json"
    props_path.write_text(json.dumps(job_state["poster_layout"]), encoding="utf-8")

    poster_png = output_dir / "poster.png"
    subprocess.run(
        [
            node_binary,
            "remotion",
            "still",
            settings.REMOTION_POSTER_COMPOSITION_ID,
            str(poster_png),
            "--props",
            str(props_path),
        ],
        cwd=settings.REMOTION_PROJECT_DIR,
        check=True,
        timeout=settings.REMOTION_RENDER_TIMEOUT_SECONDS,
    )
    return poster_png


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    raw_poster = render(job_state, settings.TMP_DIR / job_id)

    final_poster = settings.OUTPUT_DIR / job_id / "poster.png"
    final_poster.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(raw_poster, final_poster)

    job_state = state.load(job_id)
    job_state["artifacts"]["final_poster"] = str(final_poster)
    job_state["current_step"] = "PLATFORM_ADAPTOR"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
