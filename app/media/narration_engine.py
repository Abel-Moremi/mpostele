"""Narration engine: synthesizes the voiceover and measures its real duration.

Runs before composition_agent.py so scene timing can be derived from actual
narration length instead of guessed - see app/agents/composition_agent.py's
use of the "narration" state block this writes. Video path only; poster jobs
have no narration. Voiceover comes from Piper (local TTS, no network calls -
same "nothing leaves the machine" posture as the Ollama/ffmpeg/Revideo
stages). audio_engine.py (which runs later, after video_engine.py) mixes this
already-synthesized voiceover with a music bed rather than synthesizing it
itself.
"""
import json
import shutil
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state


def resolve_piper_binary() -> str:
    piper_binary = shutil.which(settings.PIPER_BINARY)
    if piper_binary is None:
        raise RuntimeError(
            f"PIPER_BINARY ({settings.PIPER_BINARY!r}) was not found on PATH. Install Piper from "
            "https://github.com/rhasspy/piper/releases and put it on PATH, or set PIPER_BINARY to "
            "its full path."
        )
    if not settings.PIPER_VOICE_MODEL:
        raise RuntimeError(
            "PIPER_VOICE_MODEL is not set. Download a voice (.onnx + .onnx.json pair) from "
            "https://huggingface.co/rhasspy/piper-voices and set PIPER_VOICE_MODEL to the .onnx path."
        )
    return piper_binary


def synthesize_voiceover(script_text: str, out_path: Path) -> None:
    piper_binary = resolve_piper_binary()
    subprocess.run(
        [
            piper_binary,
            "--model", settings.PIPER_VOICE_MODEL,
            "--output_file", str(out_path),
            "--noise_scale", str(settings.PIPER_NOISE_SCALE),
            "--noise_w", str(settings.PIPER_NOISE_W),
            "--length_scale", str(settings.PIPER_LENGTH_SCALE),
        ],
        input=script_text,
        encoding="utf-8",
        check=True,
        timeout=settings.PIPER_TIMEOUT_SECONDS,
    )


def probe_duration_seconds(media_path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "json", str(media_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    voiceover_path = output_dir / "voiceover.wav"
    synthesize_voiceover(job_state["content"]["script_text"], voiceover_path)
    duration_seconds = probe_duration_seconds(voiceover_path)

    job_state = state.load(job_id)
    job_state["artifacts"]["voiceover"] = str(voiceover_path)
    job_state["narration"] = {"duration_seconds": duration_seconds}
    job_state["current_step"] = "COMPOSITION_AGENT"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
