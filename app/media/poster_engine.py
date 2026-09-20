"""Poster rendering engine: Revideo still render (code-driven, no diffusion model).

Runs as its own subprocess - reads poster_layout from state, shells out to
the Revideo render CLI's single-frame poster render, and writes the result
back to state. Mirrors video_engine.py's subprocess pattern exactly.
"""
import json
import shutil
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.media.revideo_cli import run_revideo
from app.orchestrator import state


def render(job_state: dict, output_dir: Path) -> Path:
    props = dict(job_state["poster_layout"])
    if job_state.get("decoration_asset"):
        props["decorationSrc"] = job_state["decoration_asset"]

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "poster_props.json"
    props_path.write_text(json.dumps(props), encoding="utf-8")

    poster_png = output_dir / "poster.png"
    run_revideo("poster", props_path, poster_png)
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
