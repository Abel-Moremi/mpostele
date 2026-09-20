"""Video rendering engine: Remotion (code-driven motion graphics, no diffusion model).

Runs as its own subprocess - reads composition_spec from state, shells out to
the Remotion CLI in the sibling remotion/ Node project, and writes the
result back to state.
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

    # On Windows, npx/npm are .cmd shims - subprocess.run can't exec them
    # directly without shell=True unless resolved to their real path first.
    # shutil.which() does that resolution correctly on every platform.
    node_binary = shutil.which(settings.NODE_BINARY)
    if node_binary is None:
        raise RuntimeError(f"NODE_BINARY ({settings.NODE_BINARY!r}) was not found on PATH. Install Node.js + npm.")

    composition_spec = json.loads(json.dumps(job_state["composition_spec"]))  # deep copy before mutating
    decoration_asset = job_state.get("decoration_asset")
    if decoration_asset:
        # Only TitleReveal/Outro have a reserved corner slot for this (see
        # remotion/src/scenes/) - CaptionOverlay's word-by-word reveal has no
        # safe spot for a static accent. Attach to the first scene that can
        # take it, so every video gets at most one decoration, not one per
        # eligible scene.
        for scene in composition_spec["scenes"]:
            if scene["component"] in ("TitleReveal", "Outro"):
                scene["props"]["decorationSrc"] = decoration_asset
                break

    output_dir.mkdir(parents=True, exist_ok=True)
    props_path = output_dir / "composition_props.json"
    props_path.write_text(json.dumps(composition_spec), encoding="utf-8")

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
    job_state["artifacts"]["raw_clip"] = str(raw_clip)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
