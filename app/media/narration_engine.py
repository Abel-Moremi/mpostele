"""Narration engine: synthesizes the voiceover and measures its real duration.

Runs before composition_agent.py so scene timing can be derived from actual
narration length instead of guessed - see app/agents/composition_agent.py's
use of the "narration" state block this writes. Video path only; poster jobs
have no narration. Voiceover comes from Piper (local TTS, no network calls -
same "nothing leaves the machine" posture as the Ollama/ffmpeg/Revideo
stages).

content.script_text is split into sentences and each is synthesized (and its
real duration measured) separately, so composition_agent.py can give each
sentence its own CaptionOverlay scene sized to exactly how long it takes to
say - one continuous block reveal with no real cut points, which is what
this used to be, is a big part of why cuts felt arbitrary rather than
landing on anything. The per-segment wavs are concatenated back into a
single voiceover.wav so audio_engine.py (which runs later, after
video_engine.py) doesn't need to change at all - it still just mixes
whatever's at artifacts["voiceover"] with a music bed.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

from app.cli import parse_job_arg
from app.config import settings
from app.orchestrator import state

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


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


def split_into_segments(script_text: str) -> list:
    """Splits on sentence-ending punctuation, then folds any piece under
    settings.MIN_CAPTION_SEGMENT_CHARS into its neighbor rather than leaving
    it as its own segment - see module docstring for why a too-short segment
    matters. Accumulates into a buffer and only flushes a segment once it
    clears the threshold; a trailing remainder that never clears it folds
    into the previous segment instead of standing alone (or becomes the sole
    segment if nothing was flushed yet, e.g. the whole script is short)."""
    pieces = [p.strip() for p in _SENTENCE_SPLIT_RE.split(script_text.strip()) if p.strip()]
    if not pieces:
        return [script_text.strip()]

    segments = []
    buffer = ""
    for piece in pieces:
        buffer = f"{buffer} {piece}".strip()
        if len(buffer) >= settings.MIN_CAPTION_SEGMENT_CHARS:
            segments.append(buffer)
            buffer = ""
    if buffer:
        if segments:
            segments[-1] = f"{segments[-1]} {buffer}"
        else:
            segments.append(buffer)
    return segments


def concat_audio(segment_paths: list, out_path: Path) -> None:
    """Concatenates Piper's per-segment wavs back-to-back into the single
    voiceover file audio_engine.py expects - ffmpeg's concat demuxer with
    -c copy (no re-encode) since every segment comes from the same Piper
    voice/model and shares the same format."""
    if len(segment_paths) == 1:
        shutil.copyfile(segment_paths[0], out_path)
        return
    list_path = out_path.with_suffix(".txt")
    list_path.write_text(
        "\n".join(f"file '{p.resolve().as_posix()}'" for p in segment_paths),
        encoding="utf-8",
    )
    subprocess.run(
        ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(out_path)],
        check=True,
        capture_output=True,
        timeout=settings.AUDIO_MIX_TIMEOUT_SECONDS,
    )


def run(job_id: str) -> None:
    job_state = state.load(job_id)
    output_dir = settings.TMP_DIR / job_id
    output_dir.mkdir(parents=True, exist_ok=True)

    segment_texts = split_into_segments(job_state["content"]["script_text"])
    segments = []
    segment_paths = []
    for i, text in enumerate(segment_texts):
        segment_path = output_dir / f"voiceover_segment_{i}.wav"
        synthesize_voiceover(text, segment_path)
        segments.append({"text": text, "duration_seconds": probe_duration_seconds(segment_path)})
        segment_paths.append(segment_path)

    voiceover_path = output_dir / "voiceover.wav"
    concat_audio(segment_paths, voiceover_path)

    job_state = state.load(job_id)
    job_state["artifacts"]["voiceover"] = str(voiceover_path)
    job_state["narration"] = {
        "duration_seconds": sum(s["duration_seconds"] for s in segments),
        "segments": segments,
    }
    job_state["current_step"] = "COMPOSITION_AGENT"
    state.save(job_state)


if __name__ == "__main__":
    run(parse_job_arg())
