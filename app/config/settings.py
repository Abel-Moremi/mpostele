"""Central configuration for the mpostele pipeline."""
import os
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
ASSETS_DIR = APP_DIR / "media" / "assets"
JOBS_DIR = ASSETS_DIR / "jobs"
TMP_DIR = ASSETS_DIR / "tmp"
OUTPUT_DIR = ASSETS_DIR / "output"
FONT_DIR = ASSETS_DIR / "fonts"  # unused now that rendering is Revideo-only; kept for any future local text needs

# Persistent product context for strategy_agent.py, on top of the per-job
# input_brief (examples/*_brief.json). The per-job brief is a one-line
# campaign angle; this file carries the durable positioning/voice/audience
# detail that should stay consistent across every campaign for the same
# product, so it doesn't need to be re-typed into every brief JSON.
# Env-overridable for a future different product, same pattern as
# PIPER_VOICE_MODEL below.
PRODUCT_BRIEF_PATH = os.environ.get(
    "PRODUCT_BRIEF_PATH", str(Path(__file__).resolve().parent / "product_brief.md")
)

# Agent swarm (Ollama)
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:1.5b")
OLLAMA_TIMEOUT_SECONDS = 120
MAX_QUALITY_RETRIES = 2

# Second, larger model reserved for judgment calls the fast structured-
# extraction model (OLLAMA_MODEL) isn't well suited to - currently just
# strategy_agent.py's mood tag (see MUSIC_MOODS below). Sized for this
# project's actual hardware (an 8GB-RAM machine, often under 1GB free) -
# qwen2.5:3b (~2GB at Q4 quant) is a real step up from 1.5B without risking
# the thrashing a 7B+ model could cause here, especially with a Chromium
# render also in the picture. Like OLLAMA_MODEL, must be explicitly unloaded
# before any render subprocess spawns - see memory.py / orchestrator.py.
OLLAMA_CREATIVE_MODEL = os.environ.get("OLLAMA_CREATIVE_MODEL", "qwen2.5:3b")

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

# Sentence segmentation for CaptionOverlay (narration_engine.py splits
# content.script_text into one Piper synthesis + one scene per sentence, so
# cuts land on real speech boundaries instead of one continuous block). A
# sentence under this many characters gets merged into its neighbor before
# synthesis - Piper's duration for a very short sentence can end up close to
# or under TRANSITION_SECONDS, which would leave a transition with nothing
# to overlap and read as a flash-cut glitch rather than a real scene.
MIN_CAPTION_SEGMENT_CHARS = 25

# Scene-to-scene transition length. MUST stay in sync with
# revideo/src/transitions.ts's own TRANSITION_SECONDS constant - same
# manual-sync pattern already used for REVIDEO_WIDTH/HEIGHT/FPS against
# video-project.ts's WIDTH/HEIGHT/FPS. This doesn't add to a scene's own
# durationInFrames total (see revideo/src/video-project.ts) - it borrows a
# brief visual overlap from the outgoing scene's own tail instead.
TRANSITION_SECONDS = 0.5

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
# Single source of truth for the three placeholder tracks' mood names (keep
# in sync with generate_placeholders.py's TRACKS keys, minus ".mp3") - both
# strategy_agent.py's mood-tagging prompt and audio_engine.py's
# pick_music_track reference this rather than hardcoding the list twice.
MUSIC_MOODS = ("calm", "upbeat", "corporate")
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

# Social publishing (Postiz, self-hosted or hosted - see
# docs.postiz.com/public-api). Opt-in only, via app.main's --publish flag -
# a job's video/poster render is never blocked on this being configured.
# Default URL is the hosted instance; point at a self-hosted one instead.
POSTIZ_API_URL = os.environ.get("POSTIZ_API_URL", "https://api.postiz.com/public/v1")
POSTIZ_API_KEY = os.environ.get("POSTIZ_API_KEY")
POSTIZ_REQUEST_TIMEOUT_SECONDS = 30

# One Postiz integration (connected-account) ID per platform key
# platform_adaptor.py already produces captions for. Each account is
# connected once through Postiz's own dashboard (OAuth isn't something this
# pipeline can automate) - a platform with no ID configured here is skipped
# rather than failing the job.
POSTIZ_INTEGRATION_IDS = {
    "tiktok": os.environ.get("POSTIZ_INTEGRATION_TIKTOK"),
    "instagram": os.environ.get("POSTIZ_INTEGRATION_INSTAGRAM"),
    "x": os.environ.get("POSTIZ_INTEGRATION_X"),
    "linkedin": os.environ.get("POSTIZ_INTEGRATION_LINKEDIN"),
}
