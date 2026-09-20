"""Shared Revideo CLI invocation helper, used by poster_engine.py and video_engine.py.

Both engines need the same node-binary resolution and subprocess pattern -
factored here rather than duplicated a third time when video_engine.py grew
a second (still) render for the cover image. Mirrors the old remotion_cli.py
exactly, minus the npx shim resolution: render.mjs is our own script, run
directly with `node` (a real executable, not a .cmd shim like npx/npm).
"""
import shutil
import subprocess
from pathlib import Path

from app.config import settings


def resolve_node_binary() -> str:
    if not settings.REVIDEO_PROJECT_DIR.is_dir():
        raise RuntimeError(
            f"REVIDEO_PROJECT_DIR ({settings.REVIDEO_PROJECT_DIR}) does not exist. "
            "Run `npm install` inside revideo/ first."
        )

    node_binary = shutil.which(settings.NODE_BINARY)
    if node_binary is None:
        raise RuntimeError(f"NODE_BINARY ({settings.NODE_BINARY!r}) was not found on PATH. Install Node.js + npm.")
    return node_binary


def run_revideo(project: str, props_path: Path, out_path: Path, timeout: int = None) -> None:
    """project is "video" or "poster" - see revideo/render.mjs."""
    node_binary = resolve_node_binary()
    subprocess.run(
        [node_binary, "render.mjs", "--project", project, "--props", str(props_path), "--out", str(out_path)],
        cwd=settings.REVIDEO_PROJECT_DIR,
        check=True,
        timeout=timeout or settings.REVIDEO_RENDER_TIMEOUT_SECONDS,
    )
