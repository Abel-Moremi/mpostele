"""Central configuration for the mpostele pipeline."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "media" / "assets"
JOBS_DIR = ASSETS_DIR / "jobs"
TMP_DIR = ASSETS_DIR / "tmp"
OUTPUT_DIR = ASSETS_DIR / "output"
FONT_DIR = ASSETS_DIR / "fonts"  # unused now that rendering is Revideo-only; kept for any future local text needs

# Agent swarm (Ollama)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_TIMEOUT_SECONDS = 120
MAX_QUALITY_RETRIES = 2

# Rendering - both video and poster render via the sibling revideo/ Node
# project (headless Chromium), not a local or remote diffusion model. See
# docs-mpostele/03 Workflow/03 Video Rendering Path.md and 02 Poster
# Rendering Path.md.
NODE_BINARY = os.environ.get("NODE_BINARY", "node")
REVIDEO_PROJECT_DIR = APP_DIR.parent / "revideo"
REVIDEO_WIDTH = 1080
REVIDEO_HEIGHT = 1920
REVIDEO_FPS = 30
REVIDEO_RENDER_TIMEOUT_SECONDS = 300

# Final encode. Default was h264_nvenc, but that failed on this machine's
# driver (nvenc API 13.1 required, 13.0 found) - libx264 (software) has no
# driver dependency and is the safer out-of-the-box default; override to
# h264_nvenc if your driver supports it and you want the speedup.
VIDEO_ENCODER = os.environ.get("VIDEO_ENCODER", "libx264")
