"""Central configuration for the mpostele pipeline.

VRAM/RAM-relevant defaults live here so they stay visible and boundable,
per the Sequential Execution Contract (docs-mpostele/03 Workflow/04 Memory & Process Protocol.md).
"""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "media" / "assets"
JOBS_DIR = ASSETS_DIR / "jobs"
TMP_DIR = ASSETS_DIR / "tmp"
OUTPUT_DIR = ASSETS_DIR / "output"
FONT_DIR = ASSETS_DIR / "fonts"  # .ttf files are not bundled - place them here

# Agent swarm (Ollama)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_TIMEOUT_SECONDS = 120
MAX_QUALITY_RETRIES = 2

# Poster path (local SD1.5, hard-capped - no SDXL, see AGENTS.md)
SD15_MODEL_ID = os.environ.get("SD15_MODEL_ID", "runwayml/stable-diffusion-v1-5")
SD15_STEPS = 20
POSTER_GEN_WIDTH = 768
POSTER_GEN_HEIGHT = 1344

# Video path - local fallback. CONFIRMED NOT VIABLE on the target 1050 Ti at
# 4 or 16 frames under every configuration tried - see docs-mpostele/04
# Research/01 Local Diffusion Model Options.md. Do not rely on this path
# without re-testing after a real fix (lower resolution, a smaller
# checkpoint, or accepting >1 min/frame).
ANIMATEDIFF_MOTION_ADAPTER_ID = os.environ.get(
    "ANIMATEDIFF_MOTION_ADAPTER_ID", "guoyww/animatediff-motion-adapter-v1-5-2"
)
ANIMATEDIFF_FRAME_COUNT = 8

# Video path - remote dispatch (primary path, leaves the device - see
# docs-mpostele/03 Workflow/03 Video Rendering Path.md). Colab has no
# official job API, so this points at a small server run manually inside
# colab/wan21_server.ipynb and exposed via ngrok. The URL changes every
# time that notebook is restarted - re-set this each session.
WAN21_REMOTE_ENDPOINT = os.environ.get("WAN21_REMOTE_ENDPOINT", "")
WAN21_API_KEY = os.environ.get("WAN21_API_KEY", "")  # must match the notebook's API_KEY cell
# CONFIRMED WORKING on a live Colab T4 (2026-09-18) at these exact values,
# with the notebook using device_map="balanced" + attention_slicing +
# vae.enable_slicing()/enable_tiling() - see docs-mpostele/03 Workflow/03
# Video Rendering Path.md for the five failed configurations that preceded
# this one. Raising these is untested - increase incrementally.
WAN21_FRAME_COUNT = 9
WAN21_WIDTH = 320
WAN21_HEIGHT = 576
WAN21_POLL_INTERVAL_SECONDS = 5
WAN21_POLL_TIMEOUT_SECONDS = 900

# Interpolation / encode
RIFE_BINARY = os.environ.get("RIFE_BINARY", "")
INTERPOLATION_TARGET_FPS = 32
VIDEO_ENCODER = os.environ.get("VIDEO_ENCODER", "h264_nvenc")
