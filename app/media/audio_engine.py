"""Audio engine: synthesizes the voiceover and mixes it with a background
music bed into a single track for encode.py to mux in.

Runs after video_engine.py (needs the rendered clip's duration) and before
encode.py (which already knows how to mux a single artifacts["audio_track"]
into the final render - this is the first stage that actually produces one).
Voiceover comes from Piper (local TTS, no network calls - same "nothing
leaves the machine" posture as the Ollama/ffmpeg/Revideo stages). Music comes
from the synthesized placeholder beds in app/media/music/ - see
app/media/music/generate_placeholders.py for how those were made and how to
regenerate or replace them with licensed tracks.
"""
import hashlib
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
        [piper_binary, "--model", settings.PIPER_VOICE_MODEL, "--output_file", str(out_path)],
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


def pick_music_track(job_id: str) -> Path:
    """Deterministic per job_id (reproducible re-renders) but varied across
    jobs - no mood signal exists upstream to pick by (see strategy_brief) to
    match against yet, so a stable hash is the simplest fair choice."""
    tracks = sorted(settings.MUSIC_DIR.glob("*.mp3"))
    if not tracks:
        raise RuntimeError(f"No placeholder tracks found in {settings.MUSIC_DIR}.")
    index = int(hashlib.sha1(job_id.encode("utf-8")).hexdigest(), 16) % len(tracks)
    return tracks[index]


def mix_audio(voiceover_path: Path, music_path: Path, clip_duration: float, out_path: Path) -> None:
    fade = min(settings.AUDIO_FADE_SECONDS, max(clip_duration - 0.1, 0))
    fade_out_start = max(clip_duration - fade, 0)
    filter_complex = (
        "[0:a]aresample=44100,aformat=channel_layouts=stereo[voice];"
        "[1:a]aresample=44100,aformat=channel_layouts=stereo,"
        f"volume={settings.MUSIC_VOLUME_DB}dB,"
        f"afade=t=in:st=0:d={fade},afade=t=out:st={fade_out_start}:d={fade}[music];"
        "[voice][music]amix=inputs=2:duration=longest:normalize=0[mixed]"
    )
    subprocess.run(
        [
            "ffmpeg", "-y",
            "-i", str(voiceover_path),
            "-stream_loop", "-1", "-i", str(music_path),
            "-filter_complex", filter_complex,
            "-map", "[mixed]",
            "-t", str(clip_duration),
            str(out_path),
        ],
        check=True,
        timeout=settings.AUDIO_MIX_TIMEOUT_SECONDS,
    )


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    voiceover_path = output_dir / "voiceover.wav"
    synthesize_voiceover(job_state["content"]["script_text"], voiceover_path)

    raw_clip = Path(job_state["artifacts"]["raw_clip"])
    clip_duration = probe_duration_seconds(raw_clip)
    music_path = pick_music_track(job_id)

    audio_track_path = output_dir / "audio_track.m4a"
    mix_audio(voiceover_path, music_path, clip_duration, audio_track_path)

    job_state = state.load(job_id)
    job_state["artifacts"]["audio_track"] = str(audio_track_path)
    job_state["current_step"] = "ENCODE"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
