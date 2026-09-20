"""Shared Remotion CLI invocation helper, used by poster_engine.py and video_engine.py.

Both engines need the same node-binary resolution and subprocess pattern -
factored here rather than duplicated a third time when video_engine.py grew
a second (still) render for the cover image.
"""
import shutil
import subprocess

from app.config import settings


def resolve_node_binary() -> str:
    """On Windows, npx/npm are .cmd shims - subprocess.run can't exec them
    directly without shell=True unless resolved to their real path first.
    shutil.which() does that resolution correctly on every platform."""
    if not settings.REMOTION_PROJECT_DIR.is_dir():
        raise RuntimeError(
            f"REMOTION_PROJECT_DIR ({settings.REMOTION_PROJECT_DIR}) does not exist. "
            "Run `npm install` inside remotion/ first."
        )

    node_binary = shutil.which(settings.NODE_BINARY)
    if node_binary is None:
        raise RuntimeError(f"NODE_BINARY ({settings.NODE_BINARY!r}) was not found on PATH. Install Node.js + npm.")
    return node_binary


def run_remotion(args: list, timeout: int = None) -> None:
    """args excludes the node binary itself, e.g. ["remotion", "still", "Poster", ...]."""
    node_binary = resolve_node_binary()
    subprocess.run(
        [node_binary, *args],
        cwd=settings.REMOTION_PROJECT_DIR,
        check=True,
        timeout=timeout or settings.REMOTION_RENDER_TIMEOUT_SECONDS,
    )
