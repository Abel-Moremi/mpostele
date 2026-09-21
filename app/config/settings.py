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

# Narration-length pacing target for script_agent.py (how much narration text
# to write, via MAX_SCRIPT_CHARS) - NOT a video-duration target. The video's
# actual duration is derived from the real synthesized narration length (see
# narration_engine.py) plus the fixed title/outro beats below, not this
# constant - composition_agent.py no longer guesses toward it.
VIDEO_TARGET_DURATION_SECONDS = 30

# Fixed hold length for the two silent title-card scenes (TitleReveal/Outro -
# narration only ever covers CaptionOverlay's script_text, see
# narration_engine.py), sized against each scene's own hardcoded intro
# animation in revideo/src/scenes/ (0.6s reveal, 1.1s badge pulse) plus a
# beat of hold time to actually read the text.
TITLE_REVEAL_SECONDS = 2.5
OUTRO_HOLD_SECONDS = 3.0

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

# Voiceover (Piper, local TTS - same "nothing leaves the machine" pattern as
# Ollama/ffmpeg/Node: an external tool installed once, not managed by this
# repo). Get a binary from https://github.com/rhasspy/piper/releases and a
# voice (.onnx + .onnx.json pair) from
# https://huggingface.co/rhasspy/piper-voices, then point these at them -
# see docs-mpostele/05 Implementation/03 Setup Checklist.md. Prefer a "high"
# quality tier voice (e.g. en_US-lessac-high) over "medium"/"low" - the
# larger model is the single biggest lever on how synthetic the narration
# sounds, well worth the extra few seconds of inference time per job.
PIPER_BINARY = os.environ.get("PIPER_BINARY", "piper")
PIPER_VOICE_MODEL = os.environ.get("PIPER_VOICE_MODEL")
PIPER_TIMEOUT_SECONDS = 60

# Synthesis tuning, away from Piper's own defaults (noise_scale=0.667,
# noise_w=0.8, length_scale=1.0) - a touch more stochastic variation in
# pitch/duration reads as less flat/robotic, and a slightly slower pace
# reads as less rushed. All three are exposed as env vars so a voice that
# doesn't need the nudge isn't forced to take it.
PIPER_NOISE_SCALE = float(os.environ.get("PIPER_NOISE_SCALE", "0.75"))
PIPER_NOISE_W = float(os.environ.get("PIPER_NOISE_W", "0.9"))
PIPER_LENGTH_SCALE = float(os.environ.get("PIPER_LENGTH_SCALE", "1.05"))

# Background music. app/media/music/ holds synthesized placeholder beds
# (generate_placeholders.py) standing in for licensed tracks - audio_engine.py
# just picks a filename from this directory, so swapping in real music later
# needs no code change.
MUSIC_DIR = APP_DIR / "media" / "music"
# The placeholder tracks are already loudness-normalized to a quiet
# background level at generation time (see generate_placeholders.py's
# loudnorm=I=-23) - this is an ADDITIONAL reduction on top of that, applied
# at mix time. -21 compounded with the source's own -23ish LUFS put the
# music around -45 to -49dB (measured), inaudible on typical playback - and
# TitleReveal/Outro (TITLE_REVEAL_SECONDS/OUTRO_HOLD_SECONDS above) have no
# voiceover at all, so that silence reads as "the video has no sound" during
# those beats. A few dB under the voiceover's peaks is enough separation to
# keep speech clear without burying the music outside the voiceover's span.
MUSIC_VOLUME_DB = -9
AUDIO_FADE_SECONDS = 1.5
AUDIO_MIX_TIMEOUT_SECONDS = 60
